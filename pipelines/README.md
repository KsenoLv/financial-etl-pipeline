# PostgreSQL Data Pipelines

This directory contains two alternative approaches for importing financial transaction data into PostgreSQL.
Both pipelines produce the same normalized database structure but differ in how the transaction data is prepared before loading.

---

# Project Structure

```text
pipelines/
├── database/
│   ├── normalized_loader.py
│   ├── row_loader.py
│   └── README.md
│
└── file_normalization/
    └── single_load/
        ├── aifory.py
        ├── biso.py
        ├── jeton.py
        └── tunzer.py
```

---

# Pipeline 1 — Raw Files → PostgreSQL

## Architecture

```text
Google Drive
      │
      ▼
Raw CSV / Excel Reports
      │
      ▼
row_loader.py
      │
      ▼
Normalized PostgreSQL Table
```

## Description

This pipeline imports raw transaction reports downloaded from Google Drive.

The script automatically:

- detects the payment provider;
- loads provider-specific mapping rules;
- extracts required fields from source reports;
- normalizes dates, amounts, currencies and transaction identifiers;
- writes the records directly into PostgreSQL.

No intermediate normalized files are created.

## Example

### Source report

```text
| Transaction ID | Date                 | Amount | Currency | Status  |
|----------------|----------------------|--------|----------|---------|
| trn_8fd34...   | 23/02/2026 00:43:31  | 20     | EUR      | Pending |
```

### Raw PostgreSQL Record

Each imported row contains both the original transaction data and metadata describing where it came from.

```text
Table: raw_data

| ingestion_id | ingestion_time | raw_hash | source_file | source_row_number | raw_data | folder_1 | folder_2 | folder_3 | folder_4 | folder_depth |
|---------------|----------------|----------|-------------|-------------------|----------|----------|----------|----------|----------|--------------|
| ea48ec89... | 2026-07-16 13:50:23 | 09fc4060... | Flamingopay BISO 02.2026.csv | 351 | {"ID":"trn_zmlbte3aai","Amount":"20","Currency":"EUR","Status":"Captured","Payment Method":"iDeal", ...} | Joint accounts (Momus+JerTeam) | Flamingopay | BISO | 02.2026 | 4 |
```

The `raw_data` column stores the complete original transaction as JSON, while the remaining columns preserve file location, folder hierarchy, ingestion metadata and source information required for auditing and traceability.

## Advantages

- One-step processing.
- No intermediate files.
- Fast end-to-end import.
- Ideal for automated ETL pipelines.
- Minimal manual intervention.

---

# Pipeline 2 — Normalized Files → PostgreSQL

## Architecture

```text
Google Drive
      │
      ▼
Raw Reports
      │
      ▼
file_normalization/single_load/
      │
      ▼
Normalized CSV / Excel
      │
      ▼
normalized_loader.py
      │
      ▼
PostgreSQL
```

## Description

In this workflow each payment provider has its own standalone normalization script.
These scripts convert different report formats into a common transaction structure.
After normalization, the generated files are imported into PostgreSQL without additional transformations.

## Example

### Normalized PostgreSQL Record

```text
Table: normalized_data

| company | wallet_bank | transaction_date | pay_id | amount | currency | status | reference |
|----------|-------------|------------------|--------|--------|----------|---------|-----------|
| Momus | BISO | 2026-02-03 14:43:29 | trn_zmlbte3aai | 20.00 | EUR | Captured | Deposit |
```

## Advantages

- Modular architecture.
- Easy to test individual providers.
- Reusable normalized files.
- Convenient for debugging and validation.
- Easy to extend with new payment providers.

---

# Related Components

Provider-specific normalization scripts are located in:

```text
file_normalization/
└── single_load/
    ├── aifory.py
    ├── biso.py
    ├── jeton.py
    └── tunzer.py
```

These scripts demonstrate how different payment provider reports are transformed into a unified transaction format before loading into PostgreSQL.
The repository includes a few example processors. The production version supports additional providers using the same architecture.

---

# Summary

This project demonstrates two production-ready approaches for importing financial transaction data into PostgreSQL.

### Option 1

A single-step pipeline that reads raw reports and writes normalized data directly into PostgreSQL.

### Option 2

A modular pipeline where provider-specific processors generate normalized files before they are imported into PostgreSQL.


Both approaches produce the same normalized database schema while supporting different deployment and integration scenarios.