#!/usr/bin/env python3
"""Download files from a Google Drive folder while preserving its hierarchy.

The script authenticates with a Google service account, recursively scans a
Google Drive folder, exports supported Google Workspace files, downloads new or
changed files, and stores a local CSV cache to avoid unnecessary downloads.

Sensitive values and infrastructure-specific paths are supplied through
command-line arguments and are not stored in the source code.
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import requests
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account


DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
GOOGLE_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
PDF_MIME_TYPE = "application/pdf"

GOOGLE_EXPORTS: dict[str, tuple[str, str]] = {
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xlsx",
    ),
    "application/vnd.google-apps.document": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".docx",
    ),
    "application/vnd.google-apps.presentation": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pptx",
    ),
    "application/vnd.google-apps.drawing": (
        "image/png",
        ".png",
    ),
}

INVALID_FILENAME_CHARACTERS = re.compile(r'[<>:"|?*]')
CACHE_FIELDNAMES = [
    "file_id",
    "modified_time",
    "local_path",
    "drive_path",
    "mime_type",
]


@dataclass(frozen=True)
class AppConfig:
    """Runtime settings for the downloader."""

    credentials_file: Path
    root_folder_id: str
    destination_root: Path
    log_root: Path
    use_keyword_filter: bool
    main_keywords: tuple[str, ...]
    common_keywords: tuple[str, ...]
    skip_pdf: bool
    request_timeout: int

    @property
    def cache_file(self) -> Path:
        return self.log_root / "gdrive_download_cache.csv"

    @property
    def structure_file(self) -> Path:
        return self.log_root / "gdrive_structure.csv"

    @property
    def log_file(self) -> Path:
        return self.log_root / "gdrive_download.log"


@dataclass
class DownloadStats:
    """Counters collected during one execution."""

    copied: int = 0
    updated: int = 0
    cached: int = 0
    skipped: int = 0
    errors: int = 0


@dataclass(frozen=True)
class CacheEntry:
    """Metadata used to determine whether a Drive file changed."""

    modified_time: str
    local_path: str
    drive_path: str
    mime_type: str


class GoogleDriveDownloader:
    """Recursively download files from Google Drive."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.stats = DownloadStats()
        self.cache: dict[str, CacheEntry] = {}
        self.structure_rows: list[list[str]] = []
        self.session = requests.Session()
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self) -> DownloadStats:
        """Execute the complete download process."""

        self._validate_config()
        self.config.destination_root.mkdir(parents=True, exist_ok=True)
        self.config.log_root.mkdir(parents=True, exist_ok=True)

        self._authenticate()
        self._load_cache()

        try:
            self._scan_folder(self.config.root_folder_id)
        finally:
            # Preserve successful cache updates even when another file fails.
            self._save_structure_log()
            self._save_cache()
            self.session.close()

        return self.stats

    def _validate_config(self) -> None:
        if not self.config.credentials_file.is_file():
            raise FileNotFoundError(
                f"Service-account credentials file not found: "
                f"{self.config.credentials_file}"
            )

        if not self.config.root_folder_id.strip():
            raise ValueError("Google Drive root folder ID is empty.")

        if self.config.request_timeout <= 0:
            raise ValueError("Request timeout must be greater than zero.")

    def _authenticate(self) -> None:
        credentials = service_account.Credentials.from_service_account_file(
            str(self.config.credentials_file),
            scopes=[DRIVE_READONLY_SCOPE],
        )
        credentials.refresh(GoogleAuthRequest())

        if not credentials.token:
            raise RuntimeError("Google authentication did not return an access token.")

        self.session.headers.update(
            {"Authorization": f"Bearer {credentials.token}"}
        )
        self.logger.info("Google Drive authentication completed.")

    def _load_cache(self) -> None:
        cache_file = self.config.cache_file

        if not cache_file.exists():
            self.logger.info("Download cache does not exist; a new cache will be created.")
            return

        try:
            with cache_file.open("r", encoding="utf-8-sig", newline="") as file:
                reader = csv.DictReader(file)
                fieldnames = set(reader.fieldnames or [])

                # Backward compatibility with the previous cache column names.
                legacy_required = {"file_id", "modifiedTime", "local_path"}
                current_required = {"file_id", "modified_time", "local_path"}

                if not (
                    legacy_required.issubset(fieldnames)
                    or current_required.issubset(fieldnames)
                ):
                    self.logger.warning(
                        "Cache file has an unsupported structure and will be rebuilt: %s",
                        cache_file,
                    )
                    return

                for row in reader:
                    file_id = (row.get("file_id") or "").strip()
                    if not file_id:
                        continue

                    self.cache[file_id] = CacheEntry(
                        modified_time=(
                            row.get("modified_time")
                            or row.get("modifiedTime")
                            or ""
                        ),
                        local_path=row.get("local_path") or "",
                        drive_path=row.get("drive_path") or "",
                        mime_type=row.get("mime_type") or row.get("mimeType") or "",
                    )

            self.logger.info("Loaded %d cache entries.", len(self.cache))

        except (OSError, csv.Error) as error:
            self.logger.warning(
                "Could not read cache file; a new cache will be created: %s",
                error,
            )
            self.cache.clear()

    def _save_cache(self) -> None:
        cache_file = self.config.cache_file
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        temporary_file = cache_file.with_suffix(cache_file.suffix + ".tmp")

        try:
            with temporary_file.open("w", encoding="utf-8-sig", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=CACHE_FIELDNAMES)
                writer.writeheader()

                for file_id, entry in sorted(self.cache.items()):
                    writer.writerow(
                        {
                            "file_id": file_id,
                            "modified_time": entry.modified_time,
                            "local_path": entry.local_path,
                            "drive_path": entry.drive_path,
                            "mime_type": entry.mime_type,
                        }
                    )

            temporary_file.replace(cache_file)
            self.logger.info("Download cache saved: %s", cache_file)

        except OSError as error:
            self.stats.errors += 1
            self.logger.error("Could not save download cache: %s", error)
            temporary_file.unlink(missing_ok=True)

    def _scan_folder(self, folder_id: str, folder_path: str = "") -> None:
        page_token: str | None = None

        while True:
            params: dict[str, Any] = {
                "q": f"'{folder_id}' in parents and trashed=false",
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
                "pageSize": 1000,
                "fields": (
                    "nextPageToken,"
                    "files(id,name,mimeType,modifiedTime,size)"
                ),
            }

            if page_token:
                params["pageToken"] = page_token

            try:
                result = self._request_json(DRIVE_FILES_URL, params=params)
            except requests.RequestException as error:
                self.stats.errors += 1
                self.logger.error(
                    "Could not read Drive folder '%s': %s",
                    folder_path or folder_id,
                    error,
                )
                return

            items = result.get("files", [])
            if not isinstance(items, list):
                self.stats.errors += 1
                self.logger.error(
                    "Unexpected Google Drive response for folder '%s'.",
                    folder_path or folder_id,
                )
                return

            for item in items:
                if not isinstance(item, dict):
                    continue

                item_name = str(item.get("name") or "").strip()
                item_id = str(item.get("id") or "").strip()
                mime_type = str(item.get("mimeType") or "").strip()

                if not item_name or not item_id or not mime_type:
                    self.stats.errors += 1
                    self.logger.warning("Skipping Drive item with incomplete metadata: %s", item)
                    continue

                current_path = (
                    f"{folder_path}/{item_name}"
                    if folder_path
                    else item_name
                )

                if mime_type == GOOGLE_FOLDER_MIME_TYPE:
                    self._scan_folder(item_id, current_path)
                else:
                    self._download_file(item, current_path)

            page_token_value = result.get("nextPageToken")
            page_token = str(page_token_value) if page_token_value else None

            if page_token is None:
                break

    def _download_file(self, item: dict[str, Any], drive_path: str) -> None:
        file_id = str(item["id"])
        mime_type = str(item["mimeType"])
        modified_time = str(item.get("modifiedTime") or "")

        if self.config.skip_pdf and self._is_pdf(item):
            self.stats.skipped += 1
            self.logger.info("Skipping PDF: /%s", drive_path)
            return

        if not self._is_allowed_path(drive_path):
            self.stats.skipped += 1
            self.logger.debug("Skipping by keyword filter: /%s", drive_path)
            return

        local_file = self._build_local_path(drive_path, mime_type)
        self.structure_rows.append(list(PurePosixPath(drive_path).parts))

        if self._is_unchanged(file_id, modified_time, local_file):
            self.stats.cached += 1
            self.logger.info("Unchanged; using cached file: /%s", drive_path)
            return

        local_file.parent.mkdir(parents=True, exist_ok=True)
        existed_before = local_file.exists()

        try:
            response = self._download_response(file_id, mime_type)
            temporary_file = local_file.with_suffix(local_file.suffix + ".part")

            try:
                with temporary_file.open("wb") as file:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            file.write(chunk)

                temporary_file.replace(local_file)
            except OSError:
                temporary_file.unlink(missing_ok=True)
                raise
            finally:
                response.close()

            if existed_before:
                self.stats.updated += 1
                action = "Updated"
            else:
                self.stats.copied += 1
                action = "Downloaded"

            self.cache[file_id] = CacheEntry(
                modified_time=modified_time,
                local_path=str(local_file),
                drive_path=drive_path,
                mime_type=mime_type,
            )
            self.logger.info("%s: /%s", action, drive_path)

        except requests.HTTPError as error:
            self.stats.errors += 1
            status_code = error.response.status_code if error.response else "unknown"
            self.logger.error(
                "HTTP %s while downloading '/%s' (file ID: %s, MIME: %s): %s",
                status_code,
                drive_path,
                file_id,
                mime_type,
                error,
            )
        except (requests.RequestException, OSError) as error:
            self.stats.errors += 1
            self.logger.error(
                "Could not download '/%s' (file ID: %s, MIME: %s): %s",
                drive_path,
                file_id,
                mime_type,
                error,
            )

    def _download_response(
        self,
        file_id: str,
        mime_type: str,
    ) -> requests.Response:
        if mime_type in GOOGLE_EXPORTS:
            export_mime, _ = GOOGLE_EXPORTS[mime_type]
            url = f"{DRIVE_FILES_URL}/{file_id}/export"
            params = {"mimeType": export_mime}
        else:
            url = f"{DRIVE_FILES_URL}/{file_id}"
            params = {
                "alt": "media",
                "supportsAllDrives": "true",
            }

        response = self.session.get(
            url,
            params=params,
            timeout=self.config.request_timeout,
            stream=True,
        )
        response.raise_for_status()
        return response

    def _request_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        response = self.session.get(
            url,
            params=params,
            timeout=self.config.request_timeout,
        )
        response.raise_for_status()

        try:
            result = response.json()
        except requests.JSONDecodeError as error:
            raise requests.RequestException(
                "Google Drive returned invalid JSON."
            ) from error
        finally:
            response.close()

        if not isinstance(result, dict):
            raise requests.RequestException(
                "Google Drive returned an unexpected JSON structure."
            )

        return result

    def _is_unchanged(
        self,
        file_id: str,
        modified_time: str,
        expected_local_file: Path,
    ) -> bool:
        cached = self.cache.get(file_id)
        if cached is None:
            return False

        cached_path = Path(cached.local_path) if cached.local_path else expected_local_file

        return (
            cached.modified_time == modified_time
            and cached_path == expected_local_file
            and cached_path.exists()
        )

    def _is_allowed_path(self, drive_path: str) -> bool:
        if not self.config.use_keyword_filter:
            return True

        normalized_path = drive_path.casefold()

        if self.config.main_keywords and not any(
            keyword.casefold() in normalized_path
            for keyword in self.config.main_keywords
        ):
            return False

        return all(
            keyword.casefold() in normalized_path
            for keyword in self.config.common_keywords
        )

    def _build_local_path(self, drive_path: str, mime_type: str) -> Path:
        safe_parts = [
            self._safe_filename(part)
            for part in PurePosixPath(drive_path).parts
            if part not in {"", ".", ".."}
        ]

        if not safe_parts:
            raise ValueError(f"Could not build a local path for: {drive_path}")

        local_file = self.config.destination_root.joinpath(*safe_parts)

        export_settings = GOOGLE_EXPORTS.get(mime_type)
        if export_settings:
            _, extension = export_settings
            if local_file.suffix.casefold() != extension.casefold():
                local_file = local_file.with_name(local_file.name + extension)

        return local_file

    @staticmethod
    def _safe_filename(name: str) -> str:
        safe_name = INVALID_FILENAME_CHARACTERS.sub("_", name).strip().rstrip(".")
        return safe_name or "unnamed"

    @staticmethod
    def _is_pdf(item: dict[str, Any]) -> bool:
        file_name = str(item.get("name") or "").casefold()
        mime_type = str(item.get("mimeType") or "")
        return file_name.endswith(".pdf") or mime_type == PDF_MIME_TYPE

    def _save_structure_log(self) -> None:
        if not self.structure_rows:
            self.logger.info("No matching files were found for the structure report.")
            return

        max_depth = max(len(row) for row in self.structure_rows)
        columns = [f"level_{level}" for level in range(1, max_depth)] + ["file"]

        output_rows: list[list[str]] = []
        for row in self.structure_rows:
            folders = row[:-1]
            file_name = row[-1]
            padding = [""] * (max_depth - len(row))
            output_rows.append(folders + padding + [file_name])

        structure_file = self.config.structure_file
        temporary_file = structure_file.with_suffix(structure_file.suffix + ".tmp")

        try:
            with temporary_file.open("w", encoding="utf-8-sig", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(columns)
                writer.writerows(output_rows)

            temporary_file.replace(structure_file)
            self.logger.info("Drive structure report saved: %s", structure_file)

        except OSError as error:
            self.stats.errors += 1
            self.logger.error("Could not save Drive structure report: %s", error)
            temporary_file.unlink(missing_ok=True)


def parse_keywords(values: Iterable[str] | None) -> tuple[str, ...]:
    """Normalize repeated keyword arguments and comma-separated values."""

    keywords: list[str] = []

    for value in values or []:
        for item in value.split(","):
            keyword = item.strip()
            if keyword and keyword not in keywords:
                keywords.append(keyword)

    return tuple(keywords)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Recursively download new and changed files from a Google Drive "
            "folder while preserving the folder hierarchy."
        )
    )
    parser.add_argument(
        "--credentials-file",
        required=True,
        type=Path,
        help="Path to the Google service-account credentials JSON file.",
    )
    parser.add_argument(
        "--root-folder-id",
        required=True,
        help="Google Drive folder ID used as the scan root.",
    )
    parser.add_argument(
        "--destination-root",
        required=True,
        type=Path,
        help="Local directory where downloaded files will be stored.",
    )
    parser.add_argument(
        "--log-root",
        required=True,
        type=Path,
        help="Directory for cache, structure report, and execution log files.",
    )
    parser.add_argument(
        "--main-keyword",
        action="append",
        default=[],
        help=(
            "Path must contain at least one main keyword. May be repeated or "
            "provided as a comma-separated list."
        ),
    )
    parser.add_argument(
        "--common-keyword",
        action="append",
        default=[],
        help=(
            "Path must contain every common keyword. May be repeated or "
            "provided as a comma-separated list."
        ),
    )
    parser.add_argument(
        "--use-keyword-filter",
        action="store_true",
        help="Enable path filtering with main and common keywords.",
    )
    parser.add_argument(
        "--include-pdf",
        action="store_true",
        help="Download PDF files. PDFs are skipped by default.",
    )
    parser.add_argument(
        "--request-timeout",
        type=int,
        default=120,
        help="HTTP request timeout in seconds. Default: 120.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed debug logging.",
    )
    return parser


def configure_logging(log_file: Path, verbose: bool) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


def main() -> int:
    args = build_argument_parser().parse_args()

    config = AppConfig(
        credentials_file=args.credentials_file.expanduser().resolve(),
        root_folder_id=args.root_folder_id.strip(),
        destination_root=args.destination_root.expanduser().resolve(),
        log_root=args.log_root.expanduser().resolve(),
        use_keyword_filter=args.use_keyword_filter,
        main_keywords=parse_keywords(args.main_keyword),
        common_keywords=parse_keywords(args.common_keyword),
        skip_pdf=not args.include_pdf,
        request_timeout=args.request_timeout,
    )

    configure_logging(config.log_file, args.verbose)
    logger = logging.getLogger("copy_data_from_gd")

    try:
        stats = GoogleDriveDownloader(config).run()
    except (FileNotFoundError, ValueError, RuntimeError, OSError) as error:
        logger.exception("Download process failed: %s", error)
        return 1

    logger.info("Processing completed.")
    logger.info("New files downloaded: %d", stats.copied)
    logger.info("Changed files updated: %d", stats.updated)
    logger.info("Unchanged files skipped by cache: %d", stats.cached)
    logger.info("Files skipped by filters: %d", stats.skipped)
    logger.info("Errors: %d", stats.errors)

    return 0 if stats.errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
