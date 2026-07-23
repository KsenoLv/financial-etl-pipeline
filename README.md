# Financial ETL Pipeline

> **End-to-End Financial Data Engineering Platform** designed to automate financial data acquisition, processing, normalization, analytics and business intelligence reporting across **40+ payment providers and digital wallets**.

![Python](https://img.shields.io/badge/Python-3.x-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791)
![Microsoft Fabric](https://img.shields.io/badge/Microsoft-Fabric-purple)
![Power BI](https://img.shields.io/badge/PowerBI-Business%20Intelligence-yellow)
![MIT License](https://img.shields.io/badge/License-MIT-green)

---

## Highlights

- 🚀 **40+ payment providers and digital wallets**
- 🔄 **REST APIs, Google Drive & Automated Web Portals**
- ⚙️ **End-to-End Pipeline**
- 🗄️ **PostgreSQL + Microsoft Fabric + Delta Lake**
- 📊 **Power BI Business Intelligence**

---

# Overview

Financial ETL Pipeline is an end-to-end data engineering platform developed to automate financial data acquisition, processing, normalization and business reporting across **40+ payment providers and digital wallets**.

The platform combines financial data from different sources into one clear reporting system. It helps with daily reporting, data checks, and business analysis.
Financial organizations often receive operational and financial data from multiple providers, each exposing information through different technologies, formats and reporting standards. Some providers offer REST APIs, others distribute reports through shared cloud storage, while many only provide downloadable reports via secured administrative portals.
To solve this challenge, the platform automatically collects financial data from different sources, validates and standardizes it, and then loads it into PostgreSQL and Microsoft Fabric for analysis.

The platform manages the entire financial data process, from collecting raw files to preparing data for reporting and analytics.

- **Data Acquisition**
- **ETL Processing**
- **PostgreSQL Data Warehouse**
- **Microsoft Fabric**
- **Delta Lake**
- **Business Intelligence**
- **Power BI Reporting**

---

# Platform Scale

Current implementation includes:

- **40+ payment providers and digital wallets**
- Multiple acquisition methods (REST APIs, Google Drive, Web Automation)
- Automated daily processing pipelines
- Multi-currency transaction processing
- Historical exchange rate calculations
- Financial reconciliation
- Automatic business entity mapping (companies, casino brands and business partners)
- Standardization of payment systems across providers
- Automated classification of deposits and withdrawals
- Interactive Business Intelligence dashboards

---

# Architecture

```
External Financial Systems
        │
        ├──────── REST APIs
        │
        ├──────── Google Drive
        │
        └──────── Administrative Web Portals
                        │
                        ▼
            Automated Data Acquisition
                        │
                        ▼
               Validation & ETL Pipeline
                        │
                        ▼
                  PostgreSQL
                        │
                        ▼
               Microsoft Fabric
                        │
                        ▼
                  Delta Lake
                        │
                        ▼
             Business Data Models
                        │
                        ▼
                  Power BI Reports
```

---

# Data Acquisition

The platform automatically retrieves financial reports from heterogeneous external systems.

Supported acquisition methods include:

- REST API integrations
- Google Drive synchronization
- Automated authenticated web portal downloads

Despite completely different source formats, all collected data is transformed into a unified financial transaction model.

> **Confidentiality Notice**
>
> The data collection modules are not included in this public repository because they contain private authentication methods, customer-specific integrations, and confidential business logic.
> This repository focuses on the ETL architecture, data processing, normalization, analytics and reporting layers.

---

# Repository Structure

| Directory | Description |
|-----------|-------------|
| [`config/`](config/) | Configuration files and environment templates |
| [`ingestion/`](ingestion/) | Data acquisition layer (Google Drive synchronization, API integrations and provider-specific ingestion modules) |
| [`pipelines/`](pipelines/) | ETL pipelines for data validation, transformation and normalization |
| [`sql/`](sql/) | Database schema, SQL scripts and reporting views |
| [`fabric/`](fabric/) | Microsoft Fabric notebooks and analytical processing |
| [`powerbi/`](powerbi/) | Power BI reports, dashboards and screenshots |

---

# Business Intelligence

Power BI dashboards provide operational and financial reporting across multiple business dimensions.

The reporting layer includes:

### Financial Metrics

- Deposits
- Withdrawals
- Opening balances
- Closing balances
- Wallet balances
- Settlement calculations
- Top-up operations

### Revenue & Cost Analysis

- PSP commissions
- Affiliate commissions
- Chargebacks
- Refunds
- Operational expenses
- Financial reconciliation

### Business Analytics

- Wallet performance
- Provider performance
- Company performance
- Project reporting
- Multi-currency reporting
- Historical trend analysis

---

# Dashboard Preview

## Operational Financial Report

<p align="center">
<img src="powerbi/screenshots/wallet_performance.png" width="95%">
</p>

---

## Data Model

<p align="center">
  <img src="powerbi/screenshots/Semantic_model_example.png" width="49%">
  <img src="powerbi/screenshots/Semantic_model_example2.png" width="49%">
</p>

---

## Business KPI Dashboard

<p align="center">
<img src="powerbi/screenshots/Business_KPI_Dashboard.png" width="95%">
</p>

---

# Microsoft Fabric

Microsoft Fabric is used as the analytical layer of the platform.

Responsibilities include:

- Loading normalized PostgreSQL datasets
- Delta Lake storage
- Business transformations
- Historical exchange rate processing
- Analytical datasets
- Reporting optimization
- Additional business reporting datasets

---

## Configuration

The production solution uses environment variables for database connections, cloud storage and external integrations.
Configuration files are intentionally excluded from the public repository because they contain environment-specific settings and confidential integration details.

---

# License

MIT License.