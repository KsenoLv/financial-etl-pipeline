# PostgreSQL Data Pipelines

This directory contains two alternative approaches for loading transaction data
into PostgreSQL.

The project demonstrates two different ETL strategies:

1. **Raw-first pipeline** – source reports are first stored in a raw PostgreSQL
   table, then normalized inside the database.
2. **Pre-normalized pipeline** – reports are normalized before loading and then
   imported directly into PostgreSQL.

---

# Project Structure

```text
database/
├── normalize_raw_data.py
├── load_normalized_data.py
└── README.md
```

---

# Pipeline 1 — Raw Database Normalization

```
Source Reports
        │
        ▼
Raw PostgreSQL Table
(raw_data)
        │
        ▼
normalize_raw_data.py
        │
        ▼
Normalized PostgreSQL Table
(normalized_data)
```

### Description

This pipeline assumes that raw transaction records have already been imported
into PostgreSQL.

Each source record is stored as a JSON document together with ingestion
metadata.

The normalization script:

- reads raw records from PostgreSQL;
- identifies the payment provider;
- loads provider-specific mapping rules;
- extracts required fields from JSON;
- normalizes dates, numbers and text values;
- writes the normalized result into a dedicated PostgreSQL table.

### Advantages

- Preserves the original source data.
- Normalization rules can be modified without re-importing files.
- Suitable for enterprise ETL/ELT workflows.
- Complete audit trail is maintained.

---

# Pipeline 2 — Direct Normalized Loading

```
Source Reports
        │
        ▼
File Normalization
        │
        ▼
Normalized CSV / Excel
        │
        ▼
load_normalized_data.py
        │
        ▼
PostgreSQL
```

### Description

In this workflow transaction reports are normalized before loading into the
database.

Provider-specific normalization scripts convert different report formats into a
common schema.

The loader imports these normalized files directly into PostgreSQL.

### Advantages

- Simpler architecture.
- Fast import process.
- Suitable for smaller projects.
- Minimal database-side processing.

---

# Comparison

| Feature | Raw Database Pipeline | Direct Normalized Loading |
|----------|----------------------|---------------------------|
| Initial import | Raw records | Normalized records |
| Original source preserved | ✔ | ✖ |
| Database normalization | ✔ | ✖ |
| File normalization | ✖ | ✔ |
| Recommended for | Enterprise ETL / ELT | Small and medium projects |

---

# Related Components

The normalization rules used by these pipelines are located in the project's
configuration directory:

```text
config/
├── processors_config.py
├── processors_config_single_file.py
└── processors/
```

These configuration files define provider-specific field mappings used during
the normalization process.