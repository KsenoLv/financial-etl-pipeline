# Financial ETL Pipeline

> **End-to-End Financial Data Engineering Platform** for automated data acquisition, ETL processing, normalization, analytics and business intelligence reporting.

![Python](https://img.shields.io/badge/Python-3.x-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791)
![Microsoft Fabric](https://img.shields.io/badge/Microsoft-Fabric-6B3FA0)
![Power BI](https://img.shields.io/badge/PowerBI-Business%20Intelligence-F2C811)
![License](https://img.shields.io/badge/License-MIT-green)

---

# Overview

Financial ETL Pipeline is a complete data engineering solution designed to automate the collection, processing, normalization and reporting of financial transaction data from multiple payment providers.

The platform was built to solve a common challenge in financial operations: each provider exposes data differently. Some providers offer REST APIs, others deliver reports through shared cloud storage, while some only provide downloadable reports through administrative web portals.

Instead of treating each source individually, this platform creates a unified data acquisition layer that automatically retrieves, validates, normalizes and prepares financial data for business reporting.

The project demonstrates the complete lifecycle of financial data:

- Data Acquisition
- ETL Processing
- PostgreSQL Data Warehouse
- Microsoft Fabric
- Delta Lake
- Business Intelligence
- Power BI Reporting

---

# Architecture

<p align="center">
<img src="images/project_architecture.png" width="90%">
</p>

The platform follows a layered architecture where each component has a dedicated responsibility.

```
External Financial Systems
        │
        ├──────── REST APIs
        │
        ├──────── Google Drive
        │
        └──────── Web Portals
                    │
                    ▼
        Automated Data Acquisition
                    │
                    ▼
          Validation & ETL Processing
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
                Power BI
```

---

# Data Acquisition

One of the key components of this platform is the automated data acquisition layer.

Depending on provider capabilities, data is collected using multiple approaches:

- REST API integrations
- Google Drive synchronization
- Automated authenticated web portal downloads

This unified acquisition layer allows the platform to collect data from heterogeneous systems without requiring manual intervention.

> **Note**
>
> Some acquisition modules are intentionally excluded from this public repository because they contain proprietary authentication workflows, customer-specific integrations and confidential business logic.

---

# Technology Stack

| Category | Technologies |
|------------|----------------|
| Programming | Python |
| Database | PostgreSQL |
| Data Processing | Pandas, OpenPyXL |
| Data Warehouse | Microsoft Fabric |
| Storage | Delta Lake |
| Reporting | Power BI |
| SQL | PostgreSQL SQL, T-SQL |
| Version Control | Git |

---

# Key Features

- Automated multi-source data acquisition
- REST API integrations
- Google Drive synchronization
- Automated web portal data collection
- ETL processing pipeline
- Financial transaction normalization
- Historical exchange rate processing
- Weekly crypto rate calculations
- Commission calculations
- Modular SQL architecture
- Microsoft Fabric integration
- Delta Lake storage
- Power BI dashboards
- Business reporting layer

---

# Repository Structure

```
financial-etl-pipeline/

├── config/
├── fabric/
├── ingestion/
│   └── google_drive/
├── pipelines/
├── powerbi/
├── sql/
│
├── requirements.txt
├── LICENSE
└── README.md
```

---

# ETL Workflow

```
Data Acquisition
        │
        ▼
Validation
        │
        ▼
Raw Storage
        │
        ▼
Normalization
        │
        ▼
Reporting Views
        │
        ▼
Microsoft Fabric
        │
        ▼
Power BI
```

---

# Microsoft Fabric

Microsoft Fabric is used as the analytical layer of the platform.

Responsibilities include:

- Loading normalized PostgreSQL data
- Delta Lake storage
- Currency rate processing
- Business transformations
- Reporting datasets

---

# Power BI

Power BI provides business reporting and financial analytics on top of the processed datasets.

Dashboard examples include:

- Wallet performance
- Company performance
- Deposit / Withdrawal analysis
- Commission reporting
- Balance reconciliation
- Financial summaries

---

# Dashboard Preview

<p align="center">
<img src="powerbi/screenshots/dashboard_wallet.png" width="90%">
</p>

<p align="center">
<img src="powerbi/screenshots/data_model.png" width="90%">
</p>

<p align="center">
<img src="powerbi/screenshots/dashboard_summary.png" width="90%">
</p>

---

# Project Modules

| Module | Description |
|----------|-------------|
| config | Configuration templates |
| ingestion | Data acquisition |
| pipelines | ETL processing |
| sql | Database schema and reporting views |
| fabric | Microsoft Fabric notebooks |
| powerbi | Business Intelligence dashboards |

---

# Future Improvements

Planned enhancements include:

- Docker deployment
- CI/CD pipeline
- Automated testing
- Data Quality monitoring
- Airflow orchestration
- dbt models

---

# License

This project is licensed under the MIT License.
