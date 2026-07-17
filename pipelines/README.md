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
- applies provider-specific business rules;
- writes the normalized records directly into PostgreSQL.

No intermediate normalized files are created.

## Example

### Source report

```text
| Transaction ID | Date                 | Amount | Currency | Status  |
|----------------|----------------------|--------|----------|---------|
| trn_8fd34...   | 23/02/2026 00:43:31  | 20     | EUR      | Pending |
```

↓

### PostgreSQL

```text
| company | wallet_bank | transaction_date    | pay_id      | amount | currency | status  |
|----------|-------------|---------------------|-------------|--------|----------|---------|
| Momus    | BISO        | 2026-02-23 00:43:31 | trn_8fd34...| 20.00  | EUR      | Pending |
```

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

### Normalized CSV

```text
| company | wallet_bank | date                | pay_id      | amount | currency | status    |
|----------|-------------|---------------------|-------------|--------|----------|-----------|
| Momus    | BISO        | 2026-06-30 20:45:49 | 543d28f6... | 51.00  | EUR      | Declined  |
```

↓

### PostgreSQL

```text
| company | wallet_bank | date                | pay_id      | amount | currency | status    |
|----------|-------------|---------------------|-------------|--------|----------|-----------|
| Momus    | BISO        | 2026-06-30 20:45:49 | 543d28f6... | 51.00  | EUR      | Declined  |
```

## Advantages

- Modular architecture.
- Easy to test individual providers.
- Reusable normalized files.
- Convenient for debugging and validation.
- Easy to extend with new payment providers.

---

# Pipeline Comparison

| Feature | row_loader.py | normalized_loader.py |
|----------|----------------------|----------------------|
| Input | Raw reports | Normalized reports |
| Reads Google Drive files | ✅ | ❌ |
| Performs normalization | ✅ | ❌ |
| Uses standalone provider processors | ❌ | ✅ |
| Creates intermediate normalized files | ❌ | ✅ |
| Loads data into PostgreSQL | ✅ | ✅ |

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

The repository includes a representative subset of processors. The production version supports additional providers using the same architecture.

---

# Summary

This project demonstrates two production-ready approaches for importing financial transaction data into PostgreSQL.

### Option 1

`row_loader.py`

```text
Raw Reports
      │
      ▼
Normalization
      │
      ▼
PostgreSQL
```

A single-step pipeline that reads raw reports and writes normalized data directly into PostgreSQL.

### Option 2

```text
Raw Reports
      │
      ▼
Standalone Provider Processors
      │
      ▼
Normalized Files
      │
      ▼
normalized_loader.py
      │
      ▼
PostgreSQL
```

A modular pipeline where provider-specific processors generate normalized files before they are imported into PostgreSQL.

Both approaches produce the same normalized database schema while supporting different deployment and integration scenarios.