# SkillPulse — Real-Time Job Market & Skills-Demand Tracker

SkillPulse is an automated, production-grade MLOps pipeline built to ingest unstructured job postings, parse complex skills requirements using NLP/Regex, and train machine learning models to predict salary distributions.

## Project Structure

```text
├── notebooks/
│   ├── 01_setup_and_scrape.ipynb        # Ingests raw data from Adzuna API into MySQL (Phase 1)
│   └── 02_cleaning_and_extraction.ipynb # HTML cleansing, duplicate filtering, and skill extraction (Phase 2)
├── AI_MEMORY.md                         # Living design document tracking milestones & pipeline status
├── AI_MEMORY.pdf                        # Initial system blueprint and repository lock PDF
├── schema_mysql.sql                     # Database schema definition for MySQL
├── requirements.txt                     # Python packages and dependencies
└── .env                                 # Environment variables for database & API credentials (Git ignored)
```

## Prerequisites

1. **Python**: Python 3.8+ is recommended.
2. **MySQL Server**: A running local or remote MySQL instance.
3. **Adzuna API Credentials**: Register on Adzuna to obtain an App ID and App Key.

## Setup Instructions

### 1. Install Dependencies
Install all required libraries using pip:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory (based on your configuration) containing the following credentials:
```env
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=skillpulse

ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key
```

### 3. Initialize MySQL Database
Execute [schema_mysql.sql](file:///c:/Users/Kartik Kumar Singh/Desktop/skillpulse/schema_mysql.sql) in MySQL Workbench or your favorite SQL client to create the database and verify the five core tables:
```sql
SOURCE schema_mysql.sql;
```

### 4. Running the Pipeline
Execute the notebooks in order inside the `notebooks` directory:
1. Run [01_setup_and_scrape.ipynb](file:///c:/Users/Kartik Kumar Singh/Desktop/skillpulse/notebooks/01_setup_and_scrape.ipynb) to ingest the 6,000 raw job postings from the Adzuna API.
2. Run [02_cleaning_and_extraction.ipynb](file:///c:/Users/Kartik Kumar Singh/Desktop/skillpulse/notebooks/02_cleaning_and_extraction.ipynb) to clean descriptions, remove duplicates, and map skills to jobs.

---
For technical details on the data analysis, pipeline steps, and MLOps design decisions, see [AI_MEMORY.md](file:///c:/Users/Kartik Kumar Singh/Desktop/skillpulse/AI_MEMORY.md).
