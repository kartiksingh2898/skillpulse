# SkillPulse

**Real-Time Job Market & Skills-Demand Tracker**

SkillPulse is an end-to-end MLOps platform that scrapes tech job postings from Adzuna (India, UK, US), extracts in-demand skills with NLP/regex, stores everything in MySQL, and serves salary predictions via FastAPI and a Streamlit dashboard — with Evidently-based drift monitoring and Docker deployment.

Built by [Kartik Singh](https://github.com/kartiksingh2898).

---

## Features

- **Multi-country ingestion** — Adzuna API for India (`in`), UK (`gb`), and US (`us`)
- **Skill extraction** — 47 tech skills via regex NLP → MySQL many-to-many graph
- **Salary prediction** — Optuna-tuned XGBoost regressor (UK + US; India used for skill trends only)
- **REST API** — Health, top skills, and salary prediction endpoints
- **Analytics dashboard** — Market overview, skill intelligence, salary predictor, model diagnostics
- **MLOps** — Evidently drift reports + conditional auto-retrain
- **Docker Compose** — MySQL, API, dashboard, and optional drift job in one stack

---

## Architecture

```text
Adzuna API
    │
    ▼
Notebooks (scrape → clean → EDA → train)
    │
    ▼
MySQL  ◄──── Streamlit dashboard (analytics + predict)
    │
    ├──── FastAPI (REST: skills + predict)
    │
    └──── MLOps (drift monitor → retrain)
```

**Design choice:** DB-first pipeline — raw postings land in MySQL, not intermediate CSVs. Streamlit and FastAPI both read MySQL and load `models/xgboost_model.joblib` independently.

---

## Tech Stack

| Layer | Tools |
|--------|--------|
| Language | Python 3.8+ (Docker: 3.11) |
| Data | Adzuna API, pandas, SQLAlchemy, MySQL 8 |
| ML | XGBoost, scikit-learn, Optuna, joblib |
| Serving | FastAPI, Uvicorn, Streamlit, Plotly |
| MLOps | Evidently AI |
| Deploy | Docker, Docker Compose |

---

## Project Structure

```text
skillpulse/
├── notebooks/
│   ├── 01_setup_and_scrape.ipynb          # Adzuna → job_postings
│   ├── 02_cleaning_and_extraction.ipynb   # Clean, dedupe, skill extract
│   ├── 03_eda_and_feature_engineering.ipynb
│   └── 04_model_training.ipynb            # Optuna + XGBoost
├── app/                                   # FastAPI backend
│   ├── main.py
│   ├── db.py
│   └── models.py
├── streamlit_app/
│   └── app.py                             # Dashboard (4 views)
├── mlops/
│   ├── drift_monitor.py
│   └── retrain.py
├── models/
│   └── xgboost_model.joblib
├── data_exports/                          # Training matrices
├── eda_plots/                             # EDA / importance charts
├── drift_reports/                         # Evidently HTML + JSON
├── schema_mysql.sql
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.streamlit
├── start_services.bat                     # Windows control panel
├── requirements.txt
├── .env.example
└── AI_MEMORY.md                           # Full design / phase log
```

---

## Pipeline Phases

All seven phases are complete (v7.0).

### Phase 1 — Data Ingestion & Schema

**Notebook:** `notebooks/01_setup_and_scrape.ipynb`

- Built a **DB-first** MySQL schema with five core tables (`job_postings`, `skills`, `job_skills`, `model_runs`, `drift_reports`)
- Secure DB connectivity via `.env` + SQLAlchemy (`quote_plus` for special characters in passwords)
- Scraped Adzuna across **3 countries** (IN, GB, US) and **4 keywords** (`data scientist`, `software engineer`, `machine learning engineer`, `backend developer`)
- Rate limiting, failure handling, and paginated fetches
- Loaded **6,000** raw postings (2,000 per country) directly into `job_postings`

### Phase 2 — Cleaning & Skill Extraction

**Notebook:** `notebooks/02_cleaning_and_extraction.ipynb`

- Stripped HTML tags/entities and normalized whitespace
- Fingerprint deduplication on title + company + country + description prefix
- Reduced noise from **12,100 → 4,558** unique jobs (**62.3%** duplicate reduction)
- Regex NLP engine for **47** tech skills (languages, frameworks, databases, tools, concepts)
- Special boundary handling for C++, C#, Java, and Go
- Mapped skills on **2,570 / 4,558** jobs (**56.4%**); bulk-inserted **5,548** `job_skills` rows

### Phase 3 — EDA & Feature Engineering

**Notebook:** `notebooks/03_eda_and_feature_engineering.ipynb`

- Confirmed right-skewed salary distributions (GB skew 3.81, US 0.45)
- Standardized currencies to USD (GBP→USD 1.27, INR→USD 0.012)
- Applied `log1p` transform for stable regression targets
- **India excluded from salary training** (~57.9% missing salary); retained for skill-demand analytics
- Built skill co-occurrence heatmap (`eda_plots/`)
- Exported training matrix: **7,998 × 48** features (46 skills + `country_gb` / `country_us`) to `data_exports/`

### Phase 4 — Model Training & Optimization

**Notebook:** `notebooks/04_model_training.ipynb`

- 80/20 train/test split (6,398 / 1,600) with **5-fold CV**
- **Optuna** hyperparameter search (30 trials) minimizing validation RMSE
- Best settings include `n_estimators=191`, `max_depth=5`, `learning_rate≈0.056`, plus L1/L2 regularization
- Test metrics (log scale): **MAE 0.307**, **RMSE 0.605**, **R² 0.213**
- Back-transformed average error ≈ **$31,189 USD**
- Saved `models/xgboost_model.joblib`, feature-importance plot, and a `model_runs` DB log

> R² ≈ 21% is expected for real job-market data when using only sparse binary skill tags (no seniority, company size, or fine-grained location).

### Phase 5 — FastAPI Backend

**Package:** `app/` (`main.py`, `db.py`, `models.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service + DB connectivity |
| `GET` | `/skills/top` | Global top-N skills |
| `GET` | `/skills/top/{country}` | Top skills for `gb` / `us` / `in` |
| `POST` | `/predict` | Salary from skills + country (`gb` / `us`) |

- Runs on `http://127.0.0.1:8000` (OpenAPI docs at `/docs`)
- Sample predictions: US (Python, AWS, Docker, ML, K8s) → **~$147,652**; GB (Python, SQL, Django, React) → **~£54,357**

### Phase 6 — Streamlit Dashboard

**Entry:** `streamlit_app/app.py` → `http://localhost:8501`

| View | What it shows |
|------|----------------|
| **Market Overview** | Live counts, country mix, salary coverage, top hiring companies |
| **Skill Intelligence** | Top skills by country, co-occurrence explorer, high-value skills by avg salary |
| **Salary Predictor** | Multi-select skills + US/UK → prediction, gauge chart, matching jobs from DB |
| **Model Diagnostics** | `model_runs` history, best Optuna params, feature importance |

- Windows launcher: `start_services.bat` (starts API + dashboard together)

### Phase 7 — Drift Monitoring, Retrain & Docker

**Scripts:** `mlops/drift_monitor.py`, `mlops/retrain.py`  
**Deploy:** `Dockerfile.api`, `Dockerfile.streamlit`, `docker-compose.yml`

- **Evidently AI** compares latest live DB samples (~500) vs baseline `X_train.csv`
- Writes HTML/JSON under `drift_reports/` and rows into `drift_reports` table
- **Auto-retrain** when feature drift ≥ **30%** (or `python mlops/retrain.py --force`)
- Compose stack: MySQL 8 + API (`:8000`) + Streamlit (`:8501`) + optional `drift` profile
- Control panel options: start services, run drift, auto-retrain, force retrain

---


## Quick Start

### Prerequisites

- Python 3.8+
- MySQL 8 (or use Docker)
- [Adzuna](https://developer.adzuna.com/) App ID + Key (only needed to re-scrape)

### 1. Clone & install

```bash
git clone https://github.com/kartiksingh2898/skillpulse.git
cd skillpulse
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=skillpulse

ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key
```

### 3. Initialize the database

```sql
SOURCE schema_mysql.sql;
```

If you are building data from scratch, run notebooks `01` → `04` in order.  
If you already have a populated DB and `models/xgboost_model.joblib`, skip straight to serving.

### 4. Run locally

**Windows control panel:**

```bash
start_services.bat
```

**Or manually (two terminals):**

```bash
uvicorn app.main:app --reload
```

```bash
streamlit run streamlit_app/app.py
```

| Service | URL |
|---------|-----|
| API docs | http://127.0.0.1:8000/docs |
| Dashboard | http://localhost:8501 |

---

## Docker

```bash
docker compose up --build
```

| Service | Port |
|---------|------|
| MySQL | `3306` |
| FastAPI | `8000` |
| Streamlit | `8501` |

One-shot drift check:

```bash
docker compose --profile drift run --rm drift
```

---

## Try the API

Full endpoint list is in **Phase 5** above. Quick prediction example:

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d "{\"skills\": [\"Python\", \"AWS\", \"Docker\"], \"country\": \"us\"}"
```

Interactive docs: http://127.0.0.1:8000/docs

---

## MLOps Commands

```bash
# Compare live DB sample vs training baseline → drift_reports/
python mlops/drift_monitor.py

# Retrain if latest drift alert ≥ 30% feature drift
python mlops/retrain.py

# Force retrain regardless of drift
python mlops/retrain.py --force
```

---

## Database Schema

| Table | Role |
|-------|------|
| `job_postings` | Scraped Adzuna jobs |
| `skills` | Master skill dictionary |
| `job_skills` | Job ↔ skill mappings |
| `model_runs` | Training metrics & params |
| `drift_reports` | Evidently drift telemetry |

---

## Country Strategy

| Region | Role |
|--------|------|
| **India** | High volume for skill-demand trends; **not** used for salary training (low salary coverage) |
| **UK / US** | Near-full salary coverage → ground truth for XGBoost |

Salaries are standardized to USD (GBP→USD ≈ 1.27) and trained on `log1p` targets.

---

## Documentation

For phase-by-phase design decisions, metrics, and roadmap history, see **[AI_MEMORY.md](AI_MEMORY.md)**.

---

## License

MIT
