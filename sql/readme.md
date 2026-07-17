# SQL Schema

This directory contains the PostgreSQL database schema used by the ETL pipelines.

| SQL Schema | Used by |
|------------|---------|
| `schema/create_raw_data.sql` | `pipelines/database/raw_loader.py` |
| `schema/create_normalized_data.sql` | `pipelines/database/normalized_loader.py` |

Additional SQL objects (views, functions and procedures) are stored in their corresponding directories.

# dim_wallet_status_mapping

`dim_wallet_status_mapping` is a configuration table used to standardize transaction statuses received from different payment providers.

Each provider may use its own terminology for successful, failed, or pending transactions. This table maps those provider-specific values into a common reporting model.

## Normalized statuses

The project uses three standardized transaction statuses:

| Normalized status | Description                                                                          |
| ----------------- | ------------------------------------------------------------------------------------ |
| `Success`         | The transaction was completed successfully.                                          |
| `Pending`         | The transaction is still being processed.                                            |
| `Rejected`        | The transaction failed, was declined, cancelled, expired, or could not be processed. |

## Table structure

```text
Table: dim_wallet_status_mapping

| wallet_bank | source_status | normalized_status |
|-------------|---------------|-------------------|
| Wallet_A | Captured | Success |
| Wallet_A | Pending | Pending |
| Wallet_A | Declined | Rejected |
```

## Usage

The table is joined to the normalized transaction dataset using the payment provider and original transaction status.

```sql
LEFT JOIN dim_wallet_status_mapping AS status_mapping
    ON transactions.wallet_bank = status_mapping.wallet_bank
   AND transactions.status = status_mapping.source_status
```

The resulting normalized value is exposed as:

```sql
status_mapping.normalized_status AS norm_status
```

## Pipeline role

```text
raw_data_normalized_v2
        │
        │ wallet_bank + source status
        ▼
dim_wallet_status_mapping
        │
        │ normalized status
        ▼
main_data
```

This configuration-driven approach keeps provider-specific status rules outside the main reporting view and allows new mappings to be added without modifying the central transformation logic.

## Repository files

```text
/sql/schema/create_dim_wallet_status_mapping.sql
/sql/config/load_dim_wallet_status_mapping.sql
```

The public repository contains anonymized provider names and representative status mappings. Production provider configurations have been intentionally omitted.

# dim_wallet_transaction_type_mapping

`dim_wallet_transaction_type_mapping` is a configuration table used to standardize transaction references received from different payment providers.

Each provider uses its own values to describe transaction direction and operation type. The mapping table converts these provider-specific references into a unified transaction classification used by the central reporting view.

---

## Purpose

The table determines the normalized meaning of each source transaction reference.

For example, different providers may use values such as:

```text
Purchase
PAYMENT
sale
Receive Money
credit
```

Although the source values differ, they may all represent the same normalized transaction type:

```text
Deposit
```

The same approach is used for withdrawals, refunds, chargebacks, pending operations, and unsupported transaction types.

---

## Normalized transaction types

| Transaction type | Description                                                                    |
| ---------------- | ------------------------------------------------------------------------------ |
| `Deposit`        | Incoming financial transaction.                                                |
| `Withdrawal`     | Outgoing financial transaction.                                                |
| `Refund`         | Funds returned after a previous transaction.                                   |
| `Chargeback`     | Transaction reversed through a dispute or chargeback process.                  |
| `Pending`        | Operation that should not yet be treated as a completed deposit or withdrawal. |
| `Unknown`        | Source reference that cannot be reliably classified.                           |

---

## Table structure

```text
Table: dim_wallet_transaction_type_mapping

| wallet_bank | source_reference | transaction_type |
|-------------|------------------|------------------|
| Wallet_A | Purchase | Deposit |
| Wallet_A | Payout | Withdrawal |
| Wallet_A | Refund | Refund |
| Wallet_B | CHARGEBACK | Chargeback |
| Wallet_G | NULL | Unknown |
```

---

## Usage

The table is joined to the normalized transaction dataset using the payment provider and original transaction reference.

```sql
LEFT JOIN dim_wallet_transaction_type_mapping AS transaction_mapping
    ON transactions.wallet_bank = transaction_mapping.wallet_bank
   AND transactions.reference = transaction_mapping.source_reference
```

The normalized value is then used by the reporting view:

```sql
transaction_mapping.transaction_type AS norm_reference
```

For providers that require additional parsing or wallet-specific rules, the mapped value may be extended inside the central reporting view.

```sql
CASE
    WHEN transactions.wallet_bank = 'Wallet_Fixed_Withdrawal'
        THEN 'Withdrawal'

    WHEN transactions.wallet_bank = 'Wallet_Text_Direction'
        THEN
            CASE
                WHEN LOWER(transactions.project) LIKE '%incoming%'
                    THEN 'Deposit'

                WHEN LOWER(transactions.project) LIKE '%outgoing%'
                    THEN 'Withdrawal'

                ELSE NULL
            END

    ELSE transaction_mapping.transaction_type
END AS norm_reference
```

---

## Pipeline role

```text
raw_data_normalized_v2
        │
        │ wallet_bank + source reference
        ▼
dim_wallet_transaction_type_mapping
        │
        │ normalized transaction type
        ▼
main_data
```

The resulting `norm_reference` value controls several important calculations in `main_data`, including:

* effective transaction date;
* sign of the financial amount;
* commission direction;
* exchange-rate application;
* reporting classification.

---

## Repository files

```text
/sql/schema/create_dim_wallet_transaction_type_mapping.sql
/sql/config/load_dim_wallet_transaction_type_mapping.sql
```

The public repository contains anonymized provider names and representative transaction mappings. Production-specific providers, reference values, and proprietary classification rules have been intentionally omitted.

# Weekly Exchange Rates

The project maintains separate weekly exchange-rate datasets for cryptocurrency and fiat currency transactions.

Both datasets follow the same valuation methodology:

* each reporting period has a defined start and end date;
* the target valuation time is `23:59` on the final day of the period;
* historical market data is requested for the target date;
* the market value closest to the target timestamp is selected;
* the original source and actual rate timestamp are preserved;
* all rates are converted into a common reporting currency.

The main difference is the market data source:

| Rate type            | Data source |
| -------------------- | ----------- |
| Cryptocurrency rates | Binance API |
| Fiat currency rates  | `yfinance`  |

---

## Cryptocurrency rates

### dim_crypto_rates_weekly

`dim_crypto_rates_weekly` stores historical weekly cryptocurrency exchange rates used by the central financial reporting layer.

Cryptocurrency prices are retrieved from the Binance historical market API using one-minute candles close to the final minute of each reporting period.

```text
Binance API
     │
     │ Historical one-minute candles
     ▼
Crypto rate loader
     │
     ▼
dim_crypto_rates_weekly
```

---

## Fiat currency rates

Fiat exchange rates are collected using the `yfinance` Python library.

The fiat loader uses the same reporting-period logic as the cryptocurrency loader:

```text
period_start
       │
       ▼
period_end at 23:59
       │
       ▼
Historical market lookup
       │
       ▼
Nearest available rate
       │
       ▼
Weekly currency rate table
```

Historical foreign-exchange data is requested for the required currency pair and reporting date.

Example market symbols may include:

```text
USDEUR=X
CADEUR=X
CHFEUR=X
PLNEUR=X
```

The returned rate is associated with the corresponding weekly reporting period and stored for later use by the financial normalization layer.

---

## Shared valuation logic

Cryptocurrency and fiat loaders use the same conceptual process.

```text
Reporting period
        │
        ▼
Target valuation timestamp
        │
        ├── Cryptocurrency → Binance API
        │
        └── Fiat currency  → yfinance
        │
        ▼
Nearest available historical market rate
        │
        ▼
Weekly exchange-rate dimension
        │
        ▼
main_data
```

This provides a consistent exchange-rate methodology across both cryptocurrency and fiat transactions.

The unified approach ensures that:

* transactions from the same reporting period use the same valuation point;
* historical rates can be reproduced and audited;
* source timestamps are retained;
* fiat and cryptocurrency values are converted using equivalent period rules;
* all financial transactions can be expressed in one reporting currency.

---

## Rate source strategy

The rate source depends on the transaction currency.

```text
Transaction currency
        │
        ├── Fiat currency
        │       └── Historical FX data from yfinance
        │
        └── Cryptocurrency
                └── Historical market candles from Binance
```

Cryptocurrency rates may be resolved using:

* a direct cryptocurrency-to-reporting-currency market;
* a stablecoin conversion;
* an indirect conversion through USDT.

Fiat currencies are resolved through historical foreign-exchange pairs provided through `yfinance`.

---

## Pipeline role

```text
                    ┌────────────────────┐
                    │ Reporting periods  │
                    └─────────┬──────────┘
                              │
               ┌──────────────┴──────────────┐
               │                             │
               ▼                             ▼
        Binance API                      yfinance
               │                             │
               ▼                             ▼
  dim_crypto_rates_weekly       Weekly fiat rate dimension
               │                             │
               └──────────────┬──────────────┘
                              ▼
                 Exchange-rate reporting view
                              │
                              ▼
                          main_data
```

The exchange-rate reporting layer combines both rate sources and selects the appropriate rate according to the transaction currency and transaction date.

---

## Repository note

The public version of the repository uses demonstration reporting periods and a reduced list of currencies.

The production period configuration, operational currency list, and provider-specific rate-handling rules have been intentionally omitted.
