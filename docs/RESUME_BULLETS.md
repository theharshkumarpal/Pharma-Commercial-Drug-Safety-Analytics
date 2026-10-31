# Quantified Resume Bullets: Pharmaceutical Commercial & Drug Safety Analytics

**Target Role:** Pharmaceutical Analytics Associate / Life Sciences Consulting Analyst (Blue Matter Consulting focus)
**Profile:** Data Analyst | SQL & Power BI Developer | Pharmacovigilance & Commercial Operations Specialist

---

## Module 1: Pharmaceutical Commercial Analytics (Simulated Operations)

> **Data Disclosure:** Derived from simulated commercial sales data (28,500 transactions, fixed seed 42) modeling global pharmaceutical distribution, contract discounting, and reverse logistics across 6 markets.

### 1. Data Architecture & Dimensional Modeling (SQL & Star Schema)
> **Engineered an enterprise-grade SQL star schema (1 fact, 7 dimensions, 28,500 transactions) modeling $1.245B in net recognized pharmaceutical revenue across 6 global markets; built automated data-validation pipelines resolving duplicate transactions, orphaned keys, and reverse logistics return deductions, achieving 100% financial reconciliation and an 84.1% Gross-to-Net realization rate.**

### 2. Portfolio & Market Access Analytics (Consulting Strategy & Common-Period Benchmarking)
> **Conducted an empirical ABC/Pareto portfolio analysis segmenting 9 therapies into value tiers (top 4 brands generating 64.3% of revenue) and resolved unequal market launch windows (18 to 36 months) via a normalized FY2025 common-period benchmark; demonstrated that Japan ($63.1M) and France ($53.9M) outperformed the mature UK market ($51.2M), directing international commercial resource allocation.**

### 3. Customer RFM Segmentation & Sales Force Effectiveness (Python & Power BI)
> **Segmented 120 institutional health system accounts using rule-based RFM scoring and K-Means clustering (identifying 18 at-risk accounts representing 15% of client base) and benchmarked 24 sales representatives via headcount-normalized productivity ($53.1M/rep in specialty oncology vs $48.5M/rep in southern CNS); designed a 6-page Power BI executive suite specification with 17 DAX time-intelligence measures and out-of-sample forecasting (11.55% 6-month test-set MAPE).**

---

## Module 2: Pharmacovigilance & Drug Safety Analytics (FDA FAERS / openFDA)

> **Scientific Disclosure:** Derived from FDA FAERS spontaneous post-marketing reports. Report counts represent safety signals and reporting associations, not epidemiological incidence or causal proof.

### 4. Regulatory Data Engineering & Schema Alignment (ICH E2B(R3) & PostgreSQL)
> **Architected an ICH E2B(R3)-aligned PostgreSQL pharmacovigilance database and automated ETL pipeline ingesting spontaneous adverse-event reports from openFDA REST API; normalized patient demographics across 6 clinical age unit codes (800–805) and weights, implemented idempotent deduplication on safety report IDs, and logged structured audit trails across ingestion runs.**

### 5. Drug Safety Analytics & Web Dashboard (Flask, SQL & Plotly)
> **Developed a responsive Flask and Plotly drug safety surveillance dashboard surfacing adverse-event profiles, co-medication networks, and demographic distributions across target central nervous system medications; engineered join-safe SQL queries using distinct report-level aggregations to eliminate data inflation, communicating post-marketing safety signals with prominent scientific caveats.**

---

## Concise Alternatives (Optimized for 1-Page Resumes)

- **Option A (Commercial Operations Focus):**
  > Engineered an enterprise SQL star schema (28,500 transactions, 7 dimensions) modeling $1.245B in net recognized pharmaceutical revenue across 6 global markets; achieved 100% financial reconciliation across Gross-to-Net deductions, segmented 120 institutional accounts via RFM, and designed a 6-page Power BI suite specification with 17 DAX measures.

- **Option B (Safety & Data Engineering Focus):**
  > Built an ICH E2B(R3)-aligned data engineering pipeline in Python and PostgreSQL extracting adverse event reports from openFDA API; implemented exponential backoff, clinical age/weight normalization across international standards, and deployed an interactive Flask safety analytics dashboard monitoring drug-reaction signals.

- **Option C (Dual Commercial & Clinical Analytics Summary):**
  > Developed end-to-end pharmaceutical analytics platforms across commercial performance ($1.25B simulated net sales, GTN waterfall accounting, ABC Pareto portfolio analysis, Holt-Winters forecasting) and post-marketing drug safety (openFDA ETL, PostgreSQL, MedDRA adverse-event profiling, and Flask surveillance dashboard).

---

### Key Technical & Functional Keywords for ATS (Applicant Tracking Systems):
`Pharmaceutical Commercial Analytics`, `Life Sciences Consulting`, `Gross-to-Net (GTN)`, `Kimball Star Schema`, `Fact & Dimension Modeling`, `SQL Window Functions`, `DAX Time Intelligence`, `Power BI Executive Dashboards`, `RFM Customer Segmentation`, `Sales Force Effectiveness (SFE)`, `Reverse Logistics / Returns`, `Pharmacovigilance`, `FDA FAERS`, `openFDA REST API`, `ICH E2B(R3)`, `MedDRA Adverse Event Profiling`, `Out-of-Sample Forecasting (Holt-Winters / SARIMAX)`.
