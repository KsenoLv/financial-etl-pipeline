# Microsoft Fabric

This directory contains Microsoft Fabric notebooks used to load, transform and prepare normalized financial data for analytics and reporting.

## Architecture

```text
PostgreSQL
      │
      ▼
01_full_load_postgres_to_lakehouse
      │
      ▼
Lakehouse (transfer_data_to_fabric)
      │
      ▼
02_transfer_to_normalized_table
      │
      ▼
raw_data_normalized_v2
      │
      ▼
vw_raw_data_normalized_v2
      │
      ▼
Microsoft Fabric
      │
      ▼
Power BI
```

---

## Notebooks

### 01_full_load_postgres_to_lakehouse.ipynb

Loads data from PostgreSQL into the Microsoft Fabric Lakehouse staging table.

Main tasks:

- Connects to PostgreSQL
- Loads transaction data
- Validates the imported dataset

---

### 02_transfer_to_normalized_table.ipynb

Transforms staging data into the analytical dataset used by the reporting layer.

Main tasks:

- Standardizes the dataset
- Converts data types
- Calculates normalized financial values
- Loads the reporting table

---

## Reporting View

`vw_raw_data_normalized_v2` is the central reporting view of the platform.

Instead of duplicating data, the view applies business rules dynamically by combining normalized transactions with multiple mapping tables and reference datasets.

### Main Transformations

- Status normalization
- Transaction type normalization
- Company & project mapping
- Merchant enrichment
- Historical exchange rates
- Commission calculations
- Financial amount normalization

### Reporting Architecture

```text
raw_data_normalized_v2
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

Using a SQL view keeps all reporting logic in one place, making it easier to maintain while providing a single dataset for reporting and analysis.

---

> **Note**
>
> This public repository includes a simplified version of the Microsoft Fabric pipeline. Production notebooks, provider-specific business rules, and confidential reporting logic have been removed.