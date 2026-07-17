# PostgreSQL Data Pipelines

This directory contains two alternative approaches for loading financial transaction data into PostgreSQL.

The project demonstrates two common ETL architectures:

1. **Raw-first (ELT)** — source reports are imported into a raw PostgreSQL table and normalized afterwards.
2. **Pre-normalized (ETL)** — reports are normalized before loading and then imported directly into PostgreSQL.

---

# Project Structure

```text
database/
├── normalize_raw_data.py
├── load_normalized_data.py
└── README.md
```

---

# Pipeline 1 — Raw Database Normalization (ELT)

## Architecture

```text
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

## Description

This approach stores every imported transaction exactly as it appears in the original report.

Each row contains:

- original JSON data;
- ingestion metadata;
- file information;
- folder hierarchy;
- source row number.

The normalization process is performed afterwards inside PostgreSQL.

The script:

- reads raw records from PostgreSQL;
- detects the payment provider;
- loads provider-specific mapping rules;
- extracts required fields from JSON;
- normalizes dates, numeric values and text fields;
- applies provider-specific transformations;
- stores the final normalized dataset.

## Example

### Raw table (`raw_data`)

```text
| ingestion_id | wallet | raw_data |
|--------------|--------|--------------------------------------------------------------------------|
| 9f53...      | BISO   | {"ID":"trn_n4wvau55ds","Amount":"20","Currency":"EUR","Status":"Pending"} |
```

↓

### Normalized table (`normalized_data`)

```text
| company | wallet_bank | transaction_date    | pay_id        | amount | currency | status  |
|----------|-------------|---------------------|---------------|--------|----------|---------|
| Momus    | BISO        | 2026-02-23 00:43:31 | trn_n4wvau... | 20.00  | EUR      | Pending |
```

## Advantages

- Original source data is preserved.
- Normalization rules can be changed without importing files again.
- Full audit trail.
- Suitable for enterprise ETL / ELT environments.
- Easy to debug and validate mappings.

---

# Pipeline 2 — Direct Normalized Loading (ETL)

## Architecture

```text
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

## Description

This workflow normalizes reports before they are loaded into PostgreSQL.

Provider-specific processors convert different report formats into one unified schema.

The loader simply imports these normalized files into PostgreSQL.

## Example

### Normalized CSV

```text
| company | wallet_bank | date                | pay_id        | amount | currency | status    |
|----------|-------------|---------------------|---------------|--------|----------|-----------|
| Momus    | BISO        | 2026-06-30 20:45:49 | 543d28f6...   | 51.00  | EUR      | Declined  |
```

↓

### PostgreSQL

```text
| company | wallet_bank | date                | pay_id        | amount | currency | status    |
|----------|-------------|---------------------|---------------|--------|----------|-----------|
| Momus    | BISO        | 2026-06-30 20:45:49 | 543d28f6...   | 51.00  | EUR      | Declined  |
```

## Advantages

- Simple architecture.
- High loading speed.
- Minimal database-side processing.
- Easy deployment.
- Suitable for lightweight ETL pipelines.

---

# Architecture Comparison

| Feature | Raw Database Pipeline | Direct Loading Pipeline |
|----------|----------------------|-------------------------|
| Raw source preserved | ✅ | ❌ |
| File normalization required | ❌ | ✅ |
| Database normalization | ✅ | ❌ |
| Supports reprocessing without re-import | ✅ | ❌ |
| Processing location | PostgreSQL | File processors |
| Typical architecture | ELT | ETL |

---

# Related Components

The provider-specific mapping rules are stored separately from the database pipelines.

```text
config/
├── processors/
├── processors_config.py
└── processors_config_single_file.py
```

These configuration files define how each payment provider is normalized into the common transaction model.

---

# Summary

This repository demonstrates two production-ready approaches for building financial ETL pipelines.

**Approach 1 (ELT)** stores raw transaction data first and performs normalization inside PostgreSQL, providing maximum traceability and flexibility.
**Approach 2 (ETL)** normalizes transaction files before loading them into PostgreSQL, providing a simpler and faster processing pipeline.

Both approaches share the same normalization principles while targeting different architectural requirements.