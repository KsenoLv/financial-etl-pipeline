# Google Drive Downloader

Downloads financial reports from Google Drive while preserving the original folder structure.

This module is part of the **Data Acquisition** layer of the Financial ETL Pipeline. It synchronizes financial reports from Google Drive and prepares them for downstream ETL processing.

Although the production platform supports multiple acquisition methods (REST APIs, Google Drive and automated web portal downloads), **only the Google Drive implementation is included in this public repository**.

## Features

- Recursive folder scanning
- Shared Drive support
- Google Workspace document export
- Incremental downloads using cache
- Keyword-based filtering
- Download logging
- Folder structure report generation

## Input

- Google Drive shared folders

## Output

- Downloaded financial reports
- Preserved directory hierarchy
- Download logs

## Next Stage

Downloaded files can be processed by:

- `copy_data_from_gd.py` – loads raw data into PostgreSQL

---

> **Note**
>
> The production platform also supports REST API integrations and automated web portal data acquisition. These modules are intentionally excluded from the public repository because they contain proprietary authentication workflows and customer-specific integrations.