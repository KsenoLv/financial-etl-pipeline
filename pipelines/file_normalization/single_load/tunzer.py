"""Normalize Tunzer reports into the unified transaction schema."""

from __future__ import annotations

import argparse
import importlib.util
import logging
from pathlib import Path
from types import ModuleType

import pandas as pd

WALLET_BANK = "Tunzer"
SUPPORTED_EXTENSIONS = {".csv", ".xls", ".xlsm", ".xlsx"}
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "processors_config_single_file.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--log-dir", type=Path)
    return parser.parse_args()


def configure_logging(log_dir: Path | None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(
            logging.FileHandler(
                log_dir / f"{WALLET_BANK.lower()}.log",
                encoding="utf-8",
            )
        )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=handlers,
        force=True,
    )


def load_config(config_path: Path) -> ModuleType:
    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    spec = importlib.util.spec_from_file_location(
        "processors_config_single_file",
        config_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load configuration: {config_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_columns_config(config_module: ModuleType) -> dict:
    if hasattr(config_module, "get_processor"):
        return config_module.get_processor(WALLET_BANK)["columns"]

    for processor in config_module.PROCESSORS:
        if processor["wallet_bank"].casefold() == WALLET_BANK.casefold():
            return processor["columns"]

    raise KeyError(f"Wallet '{WALLET_BANK}' is missing from the configuration")


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace("\ufeff", "", regex=False)
    )
    return df


def read_file(file_path: Path) -> pd.DataFrame:
    if file_path.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        return clean_columns(pd.read_excel(file_path, dtype=str))

    errors: list[str] = []
    for encoding in ("utf-8-sig", "utf-8", "cp1251", "latin1"):
        try:
            return clean_columns(
                pd.read_csv(file_path, dtype=str, encoding=encoding)
            )
        except (UnicodeDecodeError, pd.errors.ParserError) as error:
            errors.append(f"{encoding}: {error}")
    raise ValueError(
        f"Unable to read CSV {file_path}. Attempts: " + "; ".join(errors[-4:])
    )


def normalize_dataframe(
    df: pd.DataFrame,
    columns_config: dict,
) -> pd.DataFrame:
    normalized = pd.DataFrame(index=df.index)

    for target_column, source_config in columns_config.items():
        if isinstance(source_config, str):
            source_column = source_config.strip()
            if source_column not in df.columns:
                raise KeyError(
                    f"Required column '{source_column}' not found. "
                    f"Available columns: {list(df.columns)}"
                )
            normalized[target_column] = (
                df[source_column]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.strip('"')
            )
            continue

        if isinstance(source_config, tuple) and len(source_config) == 2:
            source_column = str(source_config[0]).strip()
            fallback_value = str(source_config[1])

            if source_column in df.columns:
                series = df[source_column].fillna("").astype(str).str.strip()
                normalized[target_column] = series.mask(
                    series.eq(""),
                    fallback_value,
                )
            else:
                normalized[target_column] = fallback_value
            continue

        raise TypeError(
            f"Invalid mapping for '{target_column}': {source_config!r}"
        )

    return normalized


def save_result(
    df: pd.DataFrame,
    source_file: Path,
    source_dir: Path,
    output_dir: Path,
) -> Path:
    relative_path = source_file.relative_to(source_dir)
    output_file = output_dir / relative_path
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if output_file.suffix.lower() == ".csv":
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
    else:
        df.to_excel(output_file, index=False, engine="openpyxl")

    return output_file


def is_target_file(file_path: Path) -> bool:
    return (
        file_path.suffix.lower() in SUPPORTED_EXTENSIONS
        and WALLET_BANK.casefold() in str(file_path).casefold()
    )


def process_all_files(
    source_dir: Path,
    output_dir: Path,
    columns_config: dict,
) -> int:
    counters = {
        "processed": 0,
        "successful": 0,
        "failed": 0,
    }

    for file_path in source_dir.rglob("*"):
        if not file_path.is_file() or not is_target_file(file_path):
            continue

        counters["processed"] += 1
        try:
            logging.info("Processing: %s", file_path)
            source_df = read_file(file_path)
            result_df = normalize_dataframe(source_df, columns_config)
            output_file = save_result(
                result_df,
                file_path,
                source_dir,
                output_dir,
            )
            counters["successful"] += 1
            logging.info(
                "Saved %s rows to %s",
                len(result_df),
                output_file,
            )
        except Exception:
            counters["failed"] += 1
            logging.exception("Failed to process %s", file_path)

    logging.info(
        "Completed wallet=%s processed=%s successful=%s failed=%s",
        WALLET_BANK,
        counters["processed"],
        counters["successful"],
        counters["failed"],
    )
    return 1 if counters["failed"] else 0


def main() -> int:
    args = parse_args()
    configure_logging(args.log_dir)

    source_dir = args.source_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not source_dir.is_dir():
        logging.error("Source directory does not exist: %s", source_dir)
        return 2

    config_module = load_config(args.config.resolve())
    columns_config = get_columns_config(config_module)

    return process_all_files(source_dir, output_dir, columns_config)


if __name__ == "__main__":
    raise SystemExit(main())
