# Business Intelligence

# Wallet Performance Dashboard

The Wallet Performance dashboard provides a consolidated financial overview of balances, deposits, withdrawals, commissions, and payment provider performance.

<table>
<tr>

<td align="center">
<b>Wallet Performance</b><br><br>
<a href="screenshots/wallet_performance.png">
<img src="screenshots/wallet_performance.png" width="100%">
</a>
</td>

<td align="center">
<b>Provider Analysis</b><br><br>
<a href="screenshots/wallet_performance_2">
<img src="screenshots/wallet_performance_2" width="100%">
</a>
</td>

</tr>
</table>

The report supports hierarchical drill-down from provider level to wallet accounts and currencies while preserving consolidated financial metrics.

## Overview

The Business Intelligence layer provides financial and operational reporting for payment service providers (PSPs).

The reporting solution consolidates transaction data, balances, commissions, exchange rates, and business metadata into a single analytical model, allowing finance teams to monitor cash flow across multiple payment providers, projects, currencies, and payment methods.

The dashboards are built on top of the centralized `main_data` dataset produced by the Microsoft Fabric data pipeline.

---

# Reporting Architecture

```text
Google Drive / PSP Reports
            │
            ▼
      Data Collection
            │
            ▼
        PostgreSQL
            │
            ▼
     Microsoft Fabric
            │
            ▼
Normalization Pipeline
            │
            ▼
        main_data
            │
            ├──────────────┐
            │              │
            ▼              ▼
Reference Views   Reporting Views
            │              │
            └──────┬───────┘
                   ▼
          Power BI Dashboards
```

---

# Dashboard Purpose

The reporting solution provides a complete financial overview for each Payment Service Provider (PSP) over a selected reporting period.

The dashboards combine operational transactions, balances, commissions, settlements, refunds, chargebacks, and wallet activity into a single analytical view.

---

# Financial Metrics

Each dashboard presents a complete financial breakdown for every PSP, including:

## Wallet Information

- payment service provider;
- payment method;
- wallet currency.

---

## Opening Balance

- opening balance in the original currency;
- opening balance converted into EUR.

---

## Deposits

- transaction count;
- total deposited amount;
- project-level breakdown;
- deposit commissions;
- commission allocation by project.

---

## Withdrawals

- withdrawal count;
- withdrawal amount;
- project allocation;
- withdrawal commissions.

---

## Declined Transactions

- declined transaction count;
- declined transaction fees.

---

## Wallet Funding

- top-up amount;
- top-up commissions.

---

## Settlements

- settlement amount;
- settlement commissions.

---

## Refunds and Chargebacks

- refund amount;
- chargeback amount;
- related commissions.

---

## Affiliate Payments

- affiliate payout amount;
- affiliate commissions.

---

## Operational Expenses

Additional wallet expenses and operational fees that are not included in other financial categories.

---

## Closing Balance

The dashboard displays:

- Available Balance;
- Rolling Reserve;
- Hold Balance;
- Total Closing Balance;

both in the original wallet currency and in EUR.

---

# Balance Calculation

The financial balance is calculated using the complete transaction lifecycle.

```text
Opening Balance

+ Deposits
+ Top-Ups

- Withdrawals
- Deposit Fees
- Withdrawal Fees
- Declined Fees
- Settlements
- Settlement Fees
- Refunds
- Chargebacks
- Refund Fees
- Affiliate Payments
- Affiliate Fees
- Operational Expenses

= Closing Balance
```

Rolling Reserve and Hold Balance are presented separately and are included when calculating the final wallet balance.

```text
Closing Balance =
Available Balance
+ Rolling Reserve
+ Hold Balance
```

---

# Commission Calculation

Commission values are resolved using a configurable multi-level approach.

Priority order:

1. Commission reported directly by the payment provider.
2. Commission calculated from configurable provider pricing rules.

Pricing configuration may include:

- percentage fee;
- fixed fee;
- refund fee;
- chargeback fee;
- payment method;
- transaction currency.

This allows commission calculations to remain consistent even when provider reports contain incomplete information.

---

# Currency Conversion

The reporting model supports both fiat and cryptocurrency transactions.

Historical exchange rates are applied using a weekly valuation methodology.

- Cryptocurrency exchange rates are collected from Binance historical market data.
- Fiat currency exchange rates are collected using the same valuation logic through `yfinance`.

All balances are converted into EUR using the historical exchange rate corresponding to the reporting period.

---

# Data Enrichment

The reporting layer combines transactional information with analytical metadata collected from multiple operational databases.

Dedicated reporting views enrich transactions with:

- project information;
- casino metadata;
- payment methods;
- merchant information;
- country mappings;
- provider classifications;
- commission metadata;
- additional reporting dimensions.

This approach keeps the ETL pipeline independent from reporting-specific business logic while allowing multiple dashboards to share the same semantic model.

---

# Dashboard Features

The reporting solution supports:

- provider comparison;
- project comparison;
- payment method analysis;
- currency analysis;
- commission analysis;
- balance reconciliation;
- drill-down navigation;
- hierarchical reporting;
- conditional formatting;
- interactive filtering.

---

# Dashboard Preview

*(Dashboard screenshots will be added here.)*

## Wallet Performance

[ Screenshot ]

---

## Provider Analysis

[ Screenshot ]

---

## Executive Summary

[ Screenshot ]

---

# Repository Note

This repository contains documentation and representative dashboard screenshots only.

Production Power BI reports, confidential financial data, proprietary business mappings, and internal reporting models are intentionally excluded from the public repository.