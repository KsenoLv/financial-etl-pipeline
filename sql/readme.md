# SQL

This directory contains the PostgreSQL database schema, configuration tables and reporting views used by the ETL pipeline.

## Structure

| Directory | Description |
|----------|-------------|
| `schema/` | Database schema and table definitions |
| `config/` | Configuration and mapping tables |
| `views/` | Reporting and business transformation views |

## Schema

* `schema/create_raw_data.sql` → `pipelines/database/raw_loader.py`
* `schema/create_normalized_data.sql` → `pipelines/database/normalized_loader.py`

## Reporting Views

The reporting layer is built around a **central reporting view** that serves as the primary data source for Microsoft Fabric and Power BI.
Additional mapping tables and reporting views are joined to this central view to enrich transactions with:

```text
Raw Data
    │
    ▼
Normalization Pipeline
    │
    ▼
Central Reporting View
    │
    ├── Status Mapping
    ├── Transaction Type Mapping
    ├── Payment Provider Mapping
    ├── Company & Project Mapping
    ├── Commission Rules
    └── Reporting Views
    │
    ▼
Microsoft Fabric
    │
    ▼
Power BI
```

This layered architecture keeps the core transaction model independent from business-specific reporting logic while providing a single, consistent dataset for analytics and reporting.

> **Note**
>
> The public repository contains anonymized examples only. Production reporting views, provider-specific mappings and proprietary business rules have been intentionally omitted.