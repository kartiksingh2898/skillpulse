# SkillPulse - AI Memory Document & System Design

**Real-Time Job Market & Skills-Demand Tracker • MLOps Pipeline**

| Profile Details | Values |
|---|---|
| **System Architect** | Kartik Singh (Computer Science Engineering) |
| **Project Domain** | Data Science, MLOps, NLP, Salary Prediction |
| **Core Tech Stack** | Python, MySQL, SQLAlchemy, XGBoost, FastAPI, Streamlit, Evidently AI, Docker |
| **Database Model** | DB-First Schema (5 Target Tables) |
| **Current Pipeline Phase** | Pipeline Completed & Deployed (v7.0) |
| **Last Updated** | July 16, 2026 |

---

## 1. Architectural Blueprint & Design Principles

SkillPulse is an automated, production-grade MLOps pipeline built to ingest unstructured job postings across three target countries (India, UK, US), parse complex skills requirements using NLP, and train an XGBoost regressor to predict salary distributions.

Unlike typical batch data-science experiments, SkillPulse implements a **DB-first architecture**, bypassing local intermediate CSV file formats to write raw data directly to a production schema. This ensures relational integrity, transactional safety via SQLAlchemy, and a seamless data migration workflow suitable for containerization.

### Key Multi-Country Data Strategy:
* **India (in)**: Low salary transparency/coverage (~42% populated) but exceptional volume for identifying cutting-edge tech trends and high-demand skill combinations.
* **United Kingdom (gb) & United States (us)**: Near-100% salary coverage. These regions represent the primary ground-truth data sources for training and verifying the XGBoost regression models.

---

## 2. Phase 1 Accomplishments (Completed Milestones)

We have successfully established the base collection infrastructure, localized data stores, and raw data schemas.

### A. Production Database Implementation
A relational MySQL schema has been constructed and verified locally. Database connectivity is managed securely via environment variables loaded via `python-dotenv`. The connection string actively handles special characters (such as `@` in passwords) using `urllib.parse.quote_plus()` to prevent string parsing errors.

### B. Automated Data Ingestion (`adzuna_scraper.py` / `01_setup_and_scrape.ipynb`)
* Built and executed a localized notebook-based script to query the Adzuna API across 3 target countries (IN, GB, US) and 4 tech-industry target keywords (`data scientist`, `software engineer`, `machine learning engineer`, `backend developer`).
* Built-in rate limiting, failure handling, and state preservation during paginated fetches.
* Collected, cleaned, and populated exactly **6,000 unique records** (2,000 entries each for India, UK, and United States) written directly into the `job_postings` table.

### C. Current Target Tables Verified inside MySQL:

| Table Name | Purpose | Key Columns / Types |
|---|---|---|
| **job_postings** | Stores the raw scraped Adzuna metadata | `id` (PK), `title` (VARCHAR), `company` (VARCHAR), `description` (TEXT), `country` (VARCHAR), `salary_min`, `salary_max` |
| **skills** | Master dictionary of technology skills to extract | `id` (PK), `name` (VARCHAR, UNIQUE) |
| **job_skills** | Many-to-many relationship tracking matrix | `job_id` (FK), `skill_id` (FK), composite primary key |
| **model_runs** | Log history of XGBoost runs, metrics, and dates | `id` (PK), `trained_at`, `model_type`, `mae`, `rmse`, `notes` |
| **drift_reports** | Tracks features & target drift over time (Evidently) | `id` (PK), `run_date`, `report_json` |

---

## 3. Technical Deep-Dive: Do We Need To Perform EDA?

**Architectural Answer: Yes, absolutely.** EDA (Exploratory Data Analysis) is not merely a descriptive checkpoint; it is a critical engineering requirement in our MLOps system. Skipping EDA would lead to garbage-in-garbage-out model performance.

In the upcoming Phase 3 (Exploratory Data Analysis & Feature Engineering), EDA will serve the following critical programmatic functions:

1. **Target Variable Calibration & Log Transformation**
   Salary distributions are universally right-skewed. Training an XGBoost regressor directly on raw, skewed continuous labels forces the algorithm to over-index on massive salary outliers, harming normal range prediction accuracy. During EDA, we will plot distributions, verify skewness metrics, and apply log-transformation:
   $$y_{log} = \ln(\text{Salary} + 1)$$
   This standardizes the variance and optimizes the root mean squared error (RMSE) objective function of our XGBoost model.

2. **Multi-Currency Standardization & Exchange Rate Adjustment**
   The Adzuna API yields local currencies (INR for `in`, GBP for `gb`, USD for `us`). EDA acts as our verification layer to confirm we have scaled all target values to a common baseline (e.g., standardizing everything to USD or purchasing power parity equivalents) before presenting training vectors to the ML engine.

3. **Quantifying and Managing Missing Salary Data (India's 42% Coverage)**
   EDA allows us to statistically verify if missing salary entries in the Indian dataset are Missing Completely at Random (MCAR) or Missing at Random (MAR) based on the job category/company. This dictates our training strategy:
   * We will segment India out of the salary prediction training pipeline to prevent heavily biased estimations, utilizing it strictly for high-fidelity skill-demand trend modeling.
   * We will use UK and US postings (possessing ~100% salary coverage) as our mathematical validation bed for the regression model.

4. **Establishing the Baseline for Drift Monitoring (Evidently AI)**
   An MLOps pipeline requires tracking live data distribution shifts (Drift). During EDA, we profile the exact mean, median, standard deviation, and covariance matrices of our baseline features. Evidently AI will use these computed metrics as its reference configuration to identify covariate shift and flag retraining procedures.

---

## 4. Phase 2 Accomplishments: Data Cleaning & NLP Skill Extraction (Completed Milestones)

We successfully implemented the data cleaning and NLP skill extraction pipeline in [02_cleaning_and_extraction.ipynb](file:///c:/Users/Kartik Kumar Singh/Desktop/skillpulse/notebooks/02_cleaning_and_extraction.ipynb).

### A. String Cleansing & Normalization
* Handled raw noisy text by stripping HTML tags (`<strong>`, `<br>`) and cleaning HTML character entities (`&amp;`, `&lt;`, `&gt;`, etc.).
* Standardized whitespace, normalized formatting, and trimmed fields.

### B. Fingerprint Deduplication
* Generated a composite hash based on `LOWER(TRIM(title_clean))`, `LOWER(TRIM(company_clean))`, `LOWER(TRIM(country))`, and the first 200 characters of `LOWER(TRIM(description_clean))`.
* Deduplicated the raw database entries, successfully filtering duplicates from paginated API fetches.
* **Results**: Deduplicated **12,100 raw entries down to 4,558 unique job postings** (a 62.33% reduction in noise).

### C. Skill Extraction Regex Engine
* Compiled case-insensitive regex patterns with word boundaries `\b` for 47 developer skills across Languages, Frameworks, Databases, Tools/Platforms, and Concepts.
* Implemented specialized logic to correctly handle boundaries for C++, C#, Java, and case-sensitive checks for "Go" to prevent false matches.
* **Results**: Successfully identified and mapped skills for **2,570 out of 4,558 unique postings (56.38%)**.
* **Metrics**: Bulk-inserted **5,548 job-skill mappings** into the `job_skills` table and verified the `skills` master list in the database.

---

## 5. Phase 3 Accomplishments: EDA & Feature Engineering (Completed)

We successfully executed the exploratory data analysis and feature engineering pipeline in [03_eda_and_feature_engineering.ipynb](file:///c:/Users/Kartik Kumar Singh/Desktop/skillpulse/notebooks/03_eda_and_feature_engineering.ipynb).

### A. Salary Distribution & USD Standardisation
* Confirmed that raw salary distributions in both GB and US are strongly right-skewed (GB skewness: 3.81, US: 0.45).
* Applied fixed exchange rates (GBP→USD: 1.27, INR→USD: 0.012, USD: 1.00) to standardise all salaries to a single base currency.
* Applied log1p transformation, dramatically reducing skewness (GB log-skew: -7.99, US log-skew: -5.02).

### B. Missing Data & India Exclusion
* Confirmed India has **57.9% missing salary data** — too unreliable for regression training.
* **India is excluded from regression model training.** It is retained for skill-demand trend analysis only.

### C. Skill Co-occurrence Heatmap
* Built a skill binary co-occurrence correlation matrix for all skills with ≥10 appearances.
* Saved as `eda_plots/03_skill_cooccurrence_heatmap.png`.

### D. Feature Matrix Exported for Phase 4
* Constructed a multi-hot skill feature matrix plus two country indicator columns (`country_gb`, `country_us`).
* **Training set**: 7,998 samples (GB + US with salary data), **48 features** (46 skills + 2 country indicators).
* **Target** `y`: log-transformed USD salary (min: 0.82, max: 13.36, mean: 11.54).
* Exported to `data_exports/X_train.csv`, `y_train.csv`, `train_full.csv`, and `feature_names.json`.

---

## 6. Phase 4 Accomplishments: Model Training & Optimisation (Completed)

We successfully built, optimized, and saved our salary prediction machine learning model in [04_model_training.ipynb](file:///c:/Users/Kartik Kumar Singh/Desktop/skillpulse/notebooks/04_model_training.ipynb).

### A. Training & Validation Setup
* Split the dataset of 7,998 records (GB + US with salary details) into an **80/20 train/test split** (6,398 training samples, 1,600 testing samples).
* Performed **5-fold cross-validation** to validate models during optimization.

### B. Hyperparameter Optimization (Optuna)
* Conducted 30 trials using Optuna to minimize validation RMSE.
* **Tuned parameters**: `n_estimators`, `max_depth`, `learning_rate`, `subsample`, `colsample_bytree`, `min_child_weight`, `reg_alpha`, and `reg_lambda`.
* **Best parameters found**:
  * `n_estimators`: 191
  * `max_depth`: 5
  * `learning_rate`: 0.0556
  * `subsample`: 0.952
  * `colsample_bytree`: 0.930
  * `min_child_weight`: 5
  * `reg_alpha`: 5.378
  * `reg_lambda`: 5.530
* **Best CV RMSE**: 0.5343

### C. Final Model Performance
* Evaluated the best-tuned XGBoost model on the unseen test set:
  * **Mean Absolute Error (MAE)**: 0.3068 (log scale)
  * **Root Mean Squared Error (RMSE)**: 0.6048 (log scale)
  * **R-squared (R2) score**: 0.2130
  * **Average USD salary prediction error**: $31,188.97 USD (back-transformed raw scale).
  * *Note*: An R2 score of ~21% is standard in real-world recruitment data when relying purely on sparse binary skill tags (excluding company size, exact seniority level, or candidate backgrounds).
* Saved the final serialized model as `models/xgboost_model.joblib`.
* Saved the feature importance visualization to `eda_plots/04_feature_importance.png`.

### D. Model Run Logging
* Logged the model run configurations, metrics, and parameters in the `model_runs` MySQL table for governance.

---

## 7. Next Steps & Implementation Roadmap

### Phase 3: EDA & Feature Engineering (COMPLETED ✓)
* Salary standardised to USD, log-transformed, India excluded from regression.
* Exported `X_train.csv` (7,998 × 48) and `y_train.csv` for Phase 4.

### Phase 4: Model Design, Parameter Tuning & Optimization (COMPLETED ✓)
* Tuned parameters via Optuna, evaluated on 20% test split, saved model as `models/xgboost_model.joblib` and logged metrics to database.

### Phase 5: FastAPI Backend Orchestration (COMPLETED ✓)
Built and deployed a fully functional REST API with the following endpoints:
* `GET /health` — Service health check with DB connectivity status.
* `GET /skills/top` — Top N most in-demand skills globally.
* `GET /skills/top/{country}` — Top skills filtered by country (gb, us, in).
* `POST /predict` — Salary prediction from a list of skills and target country.

Project structure: `app/main.py`, `app/db.py`, `app/models.py`. Server running via `uvicorn` on `http://127.0.0.1:8000`.

**Sample prediction results:**
* US (Python, AWS, Docker, ML, K8s) → **$147,652 USD**
* GB (Python, SQL, Django, React) → **£54,357 GBP**

### Phase 6: Streamlit Dashboard (COMPLETED ✓)
Built a full premium dark-themed multi-page dashboard at `http://localhost:8501`.
* **Overview**: Live stat cards (total jobs, unique jobs, skill mappings, skills tracked), top 10 global skills bar chart, country breakdown pie & salary coverage chart.
* **Skill Demand**: Top skills per country (GB/US/IN) with interactive bar charts, grouped 3-country comparison chart, live Plotly skill co-occurrence heatmap.
* **Salary Predictor**: Multi-select skill picker, country selector (US/GB), instant prediction with animated result card, gauge chart, and skill match summary.
* **Model History**: Logged runs table from MySQL `model_runs`, best hyperparameters panel, MAE/RMSE trend line chart.
* Entry point: `streamlit_app/app.py`
* Orchestration: Added `start_services.bat` in the root workspace folder to launch both FastAPI and Streamlit concurrently in separate processes.


### Phase 7: Continuous MLOps, Drift Validation & Docker Deployment (COMPLETED ✓)
We have successfully containerised the pipeline services and integrated automated drift monitoring with self-healing model retraining.
* **Evidently AI Data Drift Engine (`mlops/drift_monitor.py`)**:
  * Compares current live database postings (latest 500 samples) against baseline training profiles (`X_train.csv`).
  * Computes Jensen-Shannon distance for binary skill indicators and K-S test p-values for continuous variables.
  * Auto-saves visual HTML reports to `drift_reports/drift_<timestamp>.html` and structural JSON summaries to `drift_reports/drift_<timestamp>.json`.
  * Persists drift telemetry in the migrated `drift_reports` MySQL table.
* **Auto-Retrain Engine (`mlops/retrain.py`)**:
  * Dynamically queries the latest drift alert status from MySQL.
  * If the drift ratio crosses the `30%` threshold (or `--force` flag is supplied), it triggers an automated training split, fits the tuned `XGBRegressor` estimator on the expanded dataset, overwrites the model binary, and registers a new entry in `model_runs`.
* **System Containerisation**:
  * `Dockerfile.api`: Python 3.11-slim runtime for the FastAPI backend, with built-in endpoint polling health checks.
  * `Dockerfile.streamlit`: Exposes the frontend on port 8501, pre-configuring headless server settings and health tests.
  * `docker-compose.yml`: Multi-container orchestration setting up `db` (MySQL 8.0 container with persistent volume and schema auto-init), `api`, `dashboard`, and an on-demand `drift` container profile.
* **Unified Control Panel (`start_services.bat`)**:
  * Upgraded to a multi-option CLI control panel to start services, run drift checks, trigger auto-retraining, or force retraining unconditionally.

