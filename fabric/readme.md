# Microsoft Fabric

This directory contains Microsoft Fabric notebooks used to transform normalized financial data into analytics-ready tables.

---

# 01_full_load_postgres_to_lakehouse.ipynb

Loads data from PostgreSQL into the Microsoft Fabric Lakehouse staging table.

## Source

```text
PostgreSQL
└── public.transfer_data_to_fabric
```

## Target

```text
Lakehouse
└── transfer_data_to_fabric
```

## Process

* Connects to PostgreSQL using JDBC.
* Reads the normalized source table.
* Converts dates and numeric values to the required schema.
* Loads the data into the Fabric Lakehouse.
* Performs basic validation after the load.

---

# 02_transfer_to_normalized_table.ipynb

Transforms data from the staging table into the main normalized table used for reporting and analytics.

## Source

```text
transfer_data_to_fabric
```

## Target

```text
raw_data_normalized_v2
```

## Process

* Reads records from the staging table.
* Converts columns to the required data types.
* Standardizes the dataset.
* Calculates the `finalamount` field (`amount × exchangerate`).
* Preserves ingestion metadata for data lineage.
* Inserts the transformed records into the normalized table.

## Output schema

```text
Table: raw_data_normalized_v2

| Company | Wallet_bank | transaction_date | depositdate | withdrawaldate | pay_id | status | amount | currency | commission | commissioncurrency | exchangerate | finalamount | project | notes | reference | paymentmethod | settlement | settlementcomission | topups | topupscomission | affilates | affilatescommission | chargebacksrefunds | chargebacksrefundscommission | expenses | expensescommission | notes222 | notes333 | notes444 | path | ingection_id | ingection_time | raw_hash |
```

## Example output

```text
Table: raw_data_normalized_v2

| Company | Wallet_bank | transaction_date | depositdate | withdrawaldate | pay_id | status | amount | currency | commission | commissioncurrency | exchangerate | finalamount | project | notes | reference | paymentmethod | settlement | settlementcomission | topups | topupscomission | affilates | affilatescommission | chargebacksrefunds | chargebacksrefundscommission | expenses | expensescommission | notes222 | notes333 | notes444 | path | ingection_id | ingection_time | raw_hash |
|---------|-------------|------------------|-------------|----------------|--------|--------|--------|----------|------------|--------------------|--------------|-------------|---------|-------|-----------|---------------|------------|----------------------|--------|-------------------|------------|----------------------|----------------------|--------------------------------|----------|--------------------|----------|----------|----------|------|--------------|----------------------------|----------|
| Momus | BISO | 2026-06-01 | 2026-06-01 19:06:28 | 2026-06-01 19:06:28 | 7fd5d9cf4ecfa31e4de3f63050b72ad1 | Pending | 51.0000 | EUR | NULL | NULL | NULL | NULL | https://betitall.com/ | NULL | Purchase | Crypto | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | /Momus/BISO/06.26/BISO Momus 01.06-07.06 2026.csv | 8f03eab4-b2d2-49f2-be3c-53e675d3f0a0 | 2026-07-16 10:33:28.847283 | 93ff19e8f49c65c8833ba4ebd3ec7d4a894443bda336896318310dc64f4d500f |
```

The resulting table serves as the primary source for reporting, reconciliation, business analytics, and downstream Microsoft Fabric transformations.

# Reporting View

## vw_raw_data_normalized_v2

`vw_raw_data_normalized_v2` is the core component of the normalization pipeline.

While the staging tables preserve the original transaction data, this view transforms heterogeneous payment provider records into a unified financial model that can be consumed by reporting tools, Power BI dashboards, and downstream analytical processes.

Rather than storing duplicated data, the view applies business rules dynamically by combining normalized transactions with multiple reference datasets.

---

## Purpose

The reporting view provides a single, consistent interface for all financial transactions regardless of the original payment provider.

Its primary objectives are:

* Normalize transaction statuses.
* Normalize transaction direction (Deposit / Withdrawal).
* Standardize transaction dates.
* Enrich transactions with merchant information.
* Apply historical exchange rates.
* Calculate commissions.
* Produce normalized financial amounts.
* Generate a reporting-ready dataset.

---

## Data Sources

The view combines data from several independent sources.

```text
raw_data_normalized_v2
        │
        ├───────────────┐
        │               │
        ▼               ▼
Status Mapping      Transaction Mapping
        │               │
        └──────┬────────┘
               ▼
      Merchant Information
               │
               ▼
      Daily Exchange Rates
               │
               ▼
      PSP Commission Rules
               │
               ▼
    vw_raw_data_normalized_v2
```

---

## Main Transformations

The view performs several normalization steps before exposing the final dataset.

### Company Normalization

Maps provider-specific projects to a unified company structure.

### Transaction Date Normalization

Determines the effective transaction date based on the transaction type while preserving the original timestamps.

### Status Normalization

Converts provider-specific statuses into a standardized reporting status.

### Transaction Type Normalization

Standardizes all transactions as either **Deposit** or **Withdrawal**.

### Merchant Enrichment

Adds merchant information using external transaction metadata.

### Exchange Rate Enrichment

Applies historical exchange rates valid at the transaction date.

### Commission Calculation

Calculates transaction commissions using either:

* provider-supplied commissions;
* configured commission rates;
* wallet-specific calculation rules.

### Financial Normalization

Produces standardized financial values including:

* original amount;
* normalized amount;
* exchange rate;
* calculated commission.

---

## Output

```text
Table: vw_raw_data_normalized_v2

| Company | Wallet_bank | transaction_date | pay_id | norm_status | amount | currency | commission | exchangerate | originalamount | finalamount | norm_project | norm_reference | paymentmethod | ... |
```

---

## Why a View?

Using a SQL view instead of storing another physical table keeps the reporting layer:

* centralized;
* consistent;
* easy to maintain;
* independent from the ingestion process.

All business logic exists in one place, allowing dashboards and analytical tools to consume a single, standardized financial dataset without duplicating transformation logic.

---

## Repository Note

The public version of this repository contains a simplified implementation of the reporting view.

The production version includes additional provider-specific normalization rules, commission models, merchant mappings, and business logic that are intentionally omitted from the public repository.
