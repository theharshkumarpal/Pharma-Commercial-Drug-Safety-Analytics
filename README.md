# Pharmaceutical Commercial Performance & Market Analytics Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![SQL](https://img.shields.io/badge/SQL-Star_Schema-orange.svg)](https://sqlite.org/)
[![Power BI](https://img.shields.io/badge/Power_BI-DAX_Measures-yellow.svg)](https://powerbi.microsoft.com/)
[![Life Sciences](https://img.shields.io/badge/Domain-Pharmaceutical_Commercial_Strategy-teal.svg)](https://www.bluematterconsulting.com/)

An end-to-end commercial analytics platform built for **Pharmaceutical Commercial Performance, Gross-to-Net (GTN) Accounting, Market Access Normalization, Customer RFM Segmentation, Sales Force Effectiveness (SFE), and Time-Series Revenue Forecasting**.

Designed to demonstrate candidate readiness for **Commercial Analytics Associate / Life Sciences Consulting Analyst** roles (e.g., Blue Matter Consulting).

---

## 1. Executive Summary & Commercial KPIs

> **Data Disclosure:** The commercial sales dataset is **synthetic transaction-level data** generated via Python (`src/generate_commercial_data.py`, fixed seed `42`) to model multi-market launches, contract discounting, and reverse logistics without exposing proprietary manufacturer audit data.

The platform models **28,500 commercial transactions** across **6 global markets** over a 36-month horizon (2023–2025), capturing **$1.245 Billion in net recognized sales** across 9 pharmaceutical therapies spanning Central Nervous System (CNS), Oncology, and Immunology.

| Metric | Empirical Value | Business Context & Definition |
| :--- | :--- | :--- |
| **Gross Invoiced Sales** | **$1,480,438,365.00** | Top-line customer orders evaluated at Wholesale Acquisition Cost (WAC). |
| **Customer Returns / Reversals** | **$2,772,950.45** | Reverse logistics refunds (batch expiration, shipping damage, cold-chain excursion). |
| **Contract Discounts & Rebates** | **$232,655,989.02** | Institutional contracting, PBM rebates, and statutory discounts (15.71% discount burden). |
| **Net Recognized Revenue** | **$1,245,009,425.53** | Realized recognized commercial cash flow (`Gross - Returns - Discounts`). |
| **Gross-to-Net (GTN) Realization** | **84.10%** | Overall commercial portfolio net revenue capture rate. |
| **Cost of Goods Sold (COGS)** | **$219,723,424.00** | Direct API formulation, sterile manufacturing, and packaging costs. |
| **Gross Margin** | **$1,025,286,001.53 (82.35%)** | Product margin supporting commercial detailing and R&D reinvestment. |
| **Net Volume Sold** | **4,898,450 Units** | Commercial units distributed across 120 key institutional healthcare accounts. |

---

## 2. Platform Architecture & Star Schema Design

The relational database is architected as a Kimball-style star schema (`fact_sales` surrounded by 7 dimension tables) implemented with integer surrogate keys and indexing:

```
                              ┌──────────────┐
                              │   dim_date   │
                              └──────┬───────┘
                                     │ date_key
       ┌────────────────┐            │            ┌───────────────┐
       │  dim_product   ├────────────┼────────────┤ dim_geography │
       └──────┬─────────┘ product_key│geography_key└───────┬───────┘
              │                      │                     │
              │         ┌────────────┴───────────┐         │
              └─────────┤       fact_sales       ├─────────┘
                        │ (Grain: 1 Invoice Line)│
              ┌─────────┤       28,500 rows      ├─────────┐
              │         └────────────┬───────────┘         │
              │ customer_key         │distributor_key      │ sales_rep_key / channel_key
       ┌──────┴─────────┐     ┌──────┴──────────┐   ┌──────┴────────┐
       │  dim_customer  │     │ dim_distributor │   │ dim_sales_rep │
       └────────────────┘     └─────────────────┘   │  dim_channel  │
                                                    └───────────────┘
```

- **`fact_sales`**: 28,500 verified rows tracking unit quantities, WAC prices, contract discounts, gross sales, return values, net sales, and return reasons.
- **`dim_date`**: Calendar date dimension supporting MoM, YoY, and common-period time intelligence.
- **`dim_product`**: 9 brand assets across CNS, Oncology, and Immunology.
- **`dim_geography`**: 6 country markets with metadata on launch dates and active coverage months.
- **`dim_customer`**: 120 institutional accounts (Academic Medical Centers, IDNs, Retail Pharmacy Chains).
- **`dim_distributor`**: Wholesale logistics intermediaries (McKesson, AmerisourceBergen/Cencora, Cardinal, Alliance, Medipal).
- **`dim_sales_rep`**: 24 field commercial representatives across 4 specialized commercial teams.
- **`dim_channel`**: 4 commercial routes to market (Hospital Direct Tender, Wholesale, Retail Chain, Specialty Mail Order).

---

## 3. Advanced Commercial Analytics Modules

### A. Product Portfolio ABC / Pareto Analysis
- **Class A Core Drivers (64.32% of revenue):** *AmphetaDex* ($293.0M), *OlanzRx* ($193.6M), *DexMethyl* ($161.4M), and *QuetiapMax* ($152.8M).
- **Class B Specialty Assets (26.35% of revenue):** *ImmunoPax* ($120.0M), *OncoShield* ($114.3M), and *EscitaloPro* ($93.9M).
- **Volume vs. Value Finding:** Oncology therapies generate **$234.3M from only 52,068 units** ($4,499/unit), whereas mature CNS therapies move 597,000+ units to yield $79.7M.

### B. Geographic Performance & Common-Period Normalization
- **The Analytical Challenge:** Countries launched at different times (US/DE/UK: 36 months; FR: 30 months; JP: 24 months; CA: 18 months).
- **The Normalized Common-Period (FY2025):** When all markets operated for a full 12 months, **Japan ($63.12M) and France ($53.91M) generated higher annualized sales than the mature UK market ($51.20M)**, highlighting expansion market velocity.

### C. Institutional Customer RFM Segmentation
- **Tier 1 Strategic Key Accounts (Champions, 37 accounts):** High frequency, high spend. Dedicated Key Account Managers assigned.
- **Tier 3 At-Risk High-Value Accounts (18 accounts):** High historical spend with purchase recency gaps > 45 days, requiring targeted field retention campaigns.

### D. Sales Force Effectiveness (SFE)
- **Headcount Normalization:** Normalized team performance by representative count across 4 teams of 6 reps each.
- **Finding:** Team Alpha (CNS North) generated $322.00M (**$53.67M/rep**) and Team Gamma (Specialty Oncology) generated $318.82M (**$53.14M/rep**), with specialty oncology achieving comparable productivity from substantially higher average transaction values.

### E. Defensible Time-Series Revenue Forecasting
- **Strict Out-of-Sample Split:** Train on first 30 months (Jan 2023–Jun 2025), Test on final 6 months (Jul 2025–Dec 2025). Zero data leakage.
- **Model Benchmark (6-Month Test Set):**
  - *Baseline Naive Persistence:* MAPE 11.85% | RMSE $7.11M
  - *Baseline 6-Month Moving Average:* MAPE 11.92% | RMSE $7.45M
  - *SARIMAX(1,1,1):* MAPE 11.86% | RMSE $6.85M
  - **Champion: Holt-Winters Exponential Smoothing (Damped Additive Trend):** **MAPE 11.55% | RMSE $6.16M** (six-month test set result).

---

## 4. Repository Structure

```text
Pharmaceutical-Commercial-Analytics/
│
├── data/
│   ├── raw/
│   │   └── pharma_commercial_sales_raw.csv    # 28,525 raw transactional records
│   └── processed/
│       ├── cleaned_sales.csv                  # 28,500 cleansed, verified transactions
│       └── pharma_commercial.db               # SQLite database with Star Schema
│
├── sql/
│   ├── 01_data_quality.sql                    # Data quality, duplicates, and orphan checks
│   ├── 02_schema.sql                          # Star Schema DDL with PK/FK constraints and indexes
│   ├── 03_transformations.sql                 # ETL staging and surrogate key mapping
│   ├── 04_kpi_analysis.sql                    # Executive GTN, MoM, and YoY calculations
│   ├── 05_product_analysis.sql                # Product portfolio & cumulative Pareto analysis
│   ├── 06_customer_analysis.sql               # Customer RFM segmentation & distributor risk
│   ├── 07_geographic_analysis.sql             # Common-period normalization & geographic velocity
│   ├── 08_sales_force_analysis.sql            # Headcount-normalized SFE & team productivity
│   └── 09_channel_analysis.sql                # Commercial channel dynamics & discount depths
│
├── src/
│   ├── generate_commercial_data.py            # Reproducible commercial dataset generator
│   ├── data_validation.py                     # Statistical validation & return integrity
│   ├── data_preprocessing.py                  # Pipeline orchestrator & star schema builder
│   ├── eda.py                                 # Statistical profiling and KPI extraction
│   ├── customer_segmentation.py               # RFM quartile scoring and K-Means clustering
│   ├── revenue_forecasting.py                 # Out-of-sample forecasting (Holt-Winters / SARIMAX)
│   └── visualizations.py                      # Consulting-style presentation figures
│
├── dashboards/
│   └── powerbi/
│       └── dax_measures.txt                   # Complete DAX measures library
│
├── outputs/
│   ├── figures/                               # Presentation-grade charts (PNG)
│   ├── reports/                               # Customer RFM tables and forecast projections (CSV)
│   └── metrics/                               # KPI summaries and forecast evaluations (JSON)
│
├── docs/
│   ├── PROJECT_AUDIT.md                       # Comprehensive baseline and transformation audit
│   ├── DATA_DICTIONARY.md                     # Data dictionary mapping fact and dimensions
│   ├── DATA_QUALITY_REPORT.md                 # Ledger of records cleansed, tagged, and retained
│   ├── BUSINESS_INSIGHTS.md                   # Strategic consulting insights and recommendations
│   ├── DASHBOARD_GUIDE.md                     # 6-page Power BI wireframes & design guide
│   ├── INTERVIEW_PREPARATION.md               # 25 consulting and technical interview Q&As
│   └── RESUME_BULLETS.md                      # Quantified, verified resume bullets
│
├── tests/
│   └── test_analytics.py                      # Automated test suite (6 tests, 100% pass)
│
├── requirements.txt                           # Python dependencies
└── README.md                                  # Project overview documentation
```

---

## 5. Quickstart & Reproducibility

### 1. Environment Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Module 1 — Commercial Analytics Pipeline
```bash
# Generate simulated commercial sales dataset (fixed seed 42)
python3 src/generate_commercial_data.py

# Clean, validate, and build the Star Schema database
python3 src/data_preprocessing.py

# Run commercial analytics, RFM segmentation, forecasting, and visualizations
python3 src/eda.py
python3 src/customer_segmentation.py
python3 src/revenue_forecasting.py
python3 src/visualizations.py
```

### 3. Run Module 2 — Pharmacovigilance ETL & Safety Dashboard
```bash
# Extract adverse event reports from openFDA API (paginated, exponential backoff)
python3 etl/extract.py

# Run transform and load into PostgreSQL schema (requires PostgreSQL DATABASE_URL in .env)
python3 run_etl.py

# Run targeted top-up for low-count therapies
python3 topup_etl.py

# Launch the interactive Flask safety surveillance dashboard
python3 -m app.app
```

### 4. Run Automated Tests
```bash
python3 -m unittest discover tests
```
*Result: 40 tests executed across 3 suites, 100% passed (zero duplicates, zero orphaned foreign keys, full financial reconciliation, age/weight unit normalization, drug brand-to-generic mappings, and join deduplication).*

---

## 6. Interview & Career Readiness

For interviewers and recruiters:
- **Project Walkthrough & Technical Questions:** Review [docs/INTERVIEW_PREPARATION.md](docs/INTERVIEW_PREPARATION.md) for 25 in-depth technical and consulting questions.
- **Consulting Insights & Recommendations:** Review [docs/BUSINESS_INSIGHTS.md](docs/BUSINESS_INSIGHTS.md) for data-driven strategic actions.
- **Resume Bullets:** Review [docs/RESUME_BULLETS.md](docs/RESUME_BULLETS.md) for ATS-ready, quantified bullets for both commercial operations and pharmacovigilance.
- **Data Dictionary:** Review [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) for relational star schema attributes and definitions.
- **Known Limitations & Caveats:** Review [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) for full scientific and synthetic disclosures.

---

## 7. Critical FAERS Scientific Limitations & Methodology

The pharmacovigilance surveillance platform utilizes spontaneous reports from the FDA Adverse Event Reporting System (FAERS) via the openFDA API:

> **Important Scientific Notice:**
> 1. **Spontaneous Reporting Nature:** FAERS is a spontaneous adverse-event reporting system. Reports are voluntarily submitted by healthcare professionals, consumers, and manufacturers.
> 2. **Incompleteness & Duplication:** Reports may be incomplete, unverified, or duplicated across reporters.
> 3. **Absence of Causality:** The existence of a report does not establish that the drug caused the adverse event. Causality cannot be inferred from FAERS data alone.
> 4. **No Incidence Denominators:** Total patient drug exposure (denominators) is not available in FAERS. Consequently, report counts cannot calculate adverse event incidence, prevalence, or true comparative safety rates.
> 5. **Reporting Biases:** Reporting rates are influenced by publicity, market tenure, media scrutiny, and regulatory alerts.
> 6. **Analytical Purpose:** Drug-reaction associations are exploratory signals for clinical investigation, not confirmed safety determinations.
> 7. **Module Independence:** The commercial analytics sales data (Module 1) and FAERS safety data (Module 2) operate independently and are not linked to imply that commercial revenue directly causes reported adverse events.
