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
