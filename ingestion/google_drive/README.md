# Google Drive Downloader

Downloads financial reports from Google Drive while preserving the original folder structure.

This module is the first stage of the ETL pipeline. It retrieves new or updated files from Google Drive and stores them locally for further processing.

## Features

- Recursive folder scanning
- Shared Drive support
- Google Workspace document export
- Incremental downloads using cache
- Keyword-based filtering
- Download logging
- Folder structure report generation

## Input

- Google Drive shared folder

## Output

## Next Stage

Downloaded files can be processed by:

- `gdrive_row.py` – loads raw data into PostgreSQL and performs normalization
- Wallet processors (e.g. `Tunzer.py`) – normalize files directly on the server