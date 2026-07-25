# ⚡ SkillPulse — Live Job Market Analytics & Autonomous MLOps Portal

**Real-Time Job Analytics, AI Salary Prediction Engine & Autonomous Cloud MLOps System**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit%20Cloud-ff4b4b?style=for-the-badge&logo=streamlit)](https://skillpulse.streamlit.app)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Daily%20Cloud%20Retrain-2088FF?style=for-the-badge&logo=github-actions)](https://github.com/kartiksingh2898/skillpulse/actions)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![XGBoost](https://img.shields.io/badge/Model-XGBoost%20Regressor-22c55e?style=for-the-badge)](https://xgboost.readthedocs.io)

SkillPulse is an end-to-end autonomous MLOps platform and job intelligence portal built on **50,200+ tech job postings** across India 🇮🇳, United States 🇺🇸, and United Kingdom 🇬🇧. It features an **Optuna-tuned XGBoost Regressor**, an **Interactive Job Application Portal** with direct Adzuna apply links, multi-currency valuation (*₹ Lakhs INR, $ USD, £ GBP*), Evidently AI drift monitoring, and **Zero-Laptop Cloud Automation** via GitHub Actions.

Built by **[Kartik Singh](https://github.com/kartiksingh2898)**.

🔗 **Live Web App:** **[https://skillpulse.streamlit.app](https://skillpulse.streamlit.app)**

---

## 🌟 Key Features

* **🌐 24/7 Live Streamlit Cloud Deployment** — Production dashboard running live at [`skillpulse.streamlit.app`](https://skillpulse.streamlit.app).
* **☁️ Zero-Laptop Cloud Automation** — GitHub Actions (`daily_refresh.yml`) automatically retrains the ML model and updates job listings every day at 05:30 AM IST in the cloud — **no local PC required!**
* **💼 Direct Job Application Portal** — Browse 750+ cached openings across India, US, and UK with direct **Apply Now →** buttons linking to Adzuna postings, quick filter chips, and 1-click fallback searches for 10,000+ live jobs.
* **💰 Multi-Currency AI Salary Engine** — Predicts tech stack valuations in **₹ Lakhs INR**, **$ USD**, and **£ GBP** using an Optuna-optimized XGBoost regressor trained on 31,500+ job records.
* **📊 Deep Skill Demand Intelligence** — Regional skill correlation heatmaps, co-occurrence network explorer, and salary-adjusted skill valuations.
* **📦 Complete MLOps Governance & Drift Monitor** — Evidently AI feature drift detection, auto-retrain triggers, and model run history tracking in MySQL.
* **⚡ One-Click Local Launcher** — `start_services.bat` handles `.venv` setup, dependency installation, MySQL database auto-creation, and non-blocking Docker fallback.

---

## 🏗️ Architecture & Automation Flow

```text
┌─────────────────────────┐       ┌─────────────────────────┐       ┌─────────────────────────┐
│  Adzuna API / MySQL DB  │       │  GitHub Actions Cloud   │       │ Streamlit Cloud         │
│  (50,200+ Job Postings) │ ────► │  (Daily 5:30 AM IST)    │ ────► │ (skillpulse.streamlit)  │
│  IN 🇮🇳 | US 🇺🇸 | GB 🇬🇧  │       │  Retrain & Export Snapshot│       │  24/7 Production App    │
└─────────────────────────┘       └─────────────────────────┘       └─────────────────────────┘
```

```text
skillpulse/
├── .github/workflows/
│   └── daily_refresh.yml                  # Cloud automation (zero-laptop daily retrain)
├── streamlit_app/
│   └── app.py                             # Premium dark glassmorphism dashboard (5 pages)
├── mlops/
│   ├── drift_monitor.py                   # Evidently AI feature drift detector
│   └── retrain.py                         # Auto-retraining pipeline script
├── scripts/
│   ├── refresh_snapshot.py                # Telemetry & job apply link exporter
│   └── setup_task.ps1                     # Local Task Scheduler installer
├── data_exports/
│   ├── db_snapshot.json                   # Cloud dataset snapshot (750+ jobs + metrics)
│   ├── train_full.csv                     # Cleaned training dataset (31,534 rows)
│   └── feature_names.json                 # 48 XGBoost model feature names
├── models/
│   └── xgboost_model.joblib               # Production trained XGBoost regressor
├── app/                                   # FastAPI REST backend
│   ├── main.py
│   ├── db.py
│   └── models.py
├── notebooks/                             # Exploratory & pipeline notebooks (Phase 1-4)
├── start_services.bat                     # Windows interactive control panel launcher
├── refresh_jobs.bat                       # One-click daily refresh batch script
├── docker-compose.yml                     # Multi-container Docker stack
└── requirements.txt                       # Project dependencies
```

---

## 🖥️ Dashboard Views

| Page | Features & Analytics |
|------|-----------------------|
| **🏠 Market Overview** | Real-time database telemetry (50,200+ postings, 31,500+ training rows), country distribution pie chart, salary transparency breakdown, and top 10 hiring companies. |
| **📊 Skill Intelligence** | Top 15 in-demand technologies by country (India, US, UK), interactive skill co-occurrence network explorer, and salary-adjusted skill valuation charts. |
| **💰 Salary Predictor** | Multi-select skill stack builder + target geography selector (**India INR**, **US USD**, **UK GBP**), interactive gauge chart, and matching job recommendations. |
| **💼 Apply for Jobs** | Filter active openings by country, skill tag, or keyword (*e.g. Google, Data Scientist, Remote*). Includes 1-click **Apply Now →** buttons and live search fallbacks. |
| **⚙️ Model Diagnostics** | Complete MLOps governance history, best Optuna hyperparameters (*n_estimators, max_depth, learning_rate*), and feature importance rankings. |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend Dashboard** | Streamlit 1.30+, Plotly Express, Glassmorphism Vanilla CSS |
| **ML & Data Engine** | XGBoost 2.0+, scikit-learn, Optuna, pandas, numpy, joblib |
| **Backend REST API** | FastAPI, Uvicorn, Pydantic, SQLAlchemy |
| **Database** | MySQL 8.0 (PyMySQL + SQLAlchemy pre-ping auto-creation) |
| **MLOps & Governance** | Evidently AI, GitHub Actions, Task Scheduler |
| **Containerization** | Docker, Docker Compose |

---

## ⚡ Quick Start

### Prerequisites
- Python 3.8+ (Python 3.11 recommended)
- MySQL 8.0 (Optional for cloud fallback mode)

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/kartiksingh2898/skillpulse.git
cd skillpulse
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)
Create a `.env` file in the root directory:
```env
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=skillpulse

ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key
```

### 3. Run Locally (One-Click)
On Windows, simply double-click **`start_services.bat`** or run:
```bash
start_services.bat
```
This launcher automatically creates your `.venv`, installs dependencies, initializes the `skillpulse` MySQL database, and launches the dashboard at **`http://localhost:8501`**.

---

## 🐳 Docker Deployment

To run the full multi-container stack (MySQL + FastAPI + Streamlit):

```bash
docker compose up --build
```

| Service | Container URL |
|---|---|
| **Streamlit Dashboard** | `http://localhost:8501` |
| **FastAPI REST Endpoints** | `http://localhost:8000/docs` |
| **MySQL Server** | `localhost:3306` |

---

## 🤖 MLOps Commands

```bash
# Force retrain the XGBoost model on the latest dataset
python mlops/retrain.py --force

# Generate Evidently AI feature drift reports
python mlops/drift_monitor.py

# Manually refresh job listings, apply URLs, and export cloud snapshot
python scripts/refresh_snapshot.py
```

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for details.

Developed with ❤️ by **[Kartik Singh](https://github.com/kartiksingh2898)**.
