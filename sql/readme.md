# SQL Schema

This directory contains the PostgreSQL database schema used by the ETL pipelines.

| SQL Schema | Used by |
|------------|---------|
| `schema/create_raw_data.sql` | `pipelines/database/raw_loader.py` |
| `schema/create_normalized_data.sql` | `pipelines/database/normalized_loader.py` |

Additional SQL objects (views, functions and procedures) are stored in their corresponding directories.