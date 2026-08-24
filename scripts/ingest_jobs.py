"""
SkillPulse - Automated Job Ingestion & Skill Extraction Engine
=============================================================
Fetches latest job postings from Adzuna API for target countries (IN, US, GB),
cleans HTML/text, deduplicates, extracts 47 tech skills using NLP regex,
and persists records into MySQL tables: `job_postings`, `skills`, and `job_skills`.

Can be executed standalone or imported by `scripts/refresh_snapshot.py`.
"""

import os
import re
import sys
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
import requests
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, Table, MetaData
from sqlalchemy.dialects.mysql import insert as mysql_insert

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("ingest_jobs")

# ── 47 Canonical Skills & Regex Patterns ─────────────────────────────────────
SKILLS_PATTERNS = {
    # Languages
    'Python': re.compile(r'\b(python|py)\b', re.IGNORECASE),
    'R': re.compile(r'\b(r\s*language|r-project)\b|\bR\b'),
    'SQL': re.compile(r'\b(sql|mysql|postgresql|postgres|pl/sql|tsql|t-sql|sqlite)\b', re.IGNORECASE),
    'JavaScript': re.compile(r'\b(javascript|js|es6)\b', re.IGNORECASE),
    'TypeScript': re.compile(r'\b(typescript|ts)\b', re.IGNORECASE),
    'Java': re.compile(r'\b(java)\b', re.IGNORECASE),
    'C++': re.compile(r'\bc\+\+\b', re.IGNORECASE),
    'C#': re.compile(r'\bc#|c-sharp\b', re.IGNORECASE),
    'Go': re.compile(r'\b(golang|go\s*lang)\b|\bGo\b'),
    'Ruby': re.compile(r'\b(ruby|rails)\b', re.IGNORECASE),
    'Rust': re.compile(r'\b(rust)\b', re.IGNORECASE),
    'HTML/CSS': re.compile(r'\b(html5?|css3?|sass|scss|less)\b', re.IGNORECASE),
    'PHP': re.compile(r'\b(php)\b', re.IGNORECASE),
    'Kotlin': re.compile(r'\b(kotlin)\b', re.IGNORECASE),
    'Swift': re.compile(r'\b(swift)\b', re.IGNORECASE),
    
    # Frameworks
    'React': re.compile(r'\b(react|reactjs|react\.js)\b', re.IGNORECASE),
    'Angular': re.compile(r'\b(angular|angularjs|angular\.js)\b', re.IGNORECASE),
    'Vue': re.compile(r'\b(vue|vuejs|vue\.js)\b', re.IGNORECASE),
    'FastAPI': re.compile(r'\b(fastapi|fast-api)\b', re.IGNORECASE),
    'Flask': re.compile(r'\b(flask)\b', re.IGNORECASE),
    'Django': re.compile(r'\b(django)\b', re.IGNORECASE),
    'Node.js': re.compile(r'\b(node|nodejs|node\.js)\b', re.IGNORECASE),
    'Spring Boot': re.compile(r'\b(spring\s*boot|spring\s*mvc|spring)\b', re.IGNORECASE),
    'Next.js': re.compile(r'\b(nextjs|next\.js)\b', re.IGNORECASE),
    
    # Databases
    'MongoDB': re.compile(r'\b(mongo|mongodb)\b', re.IGNORECASE),
    'Redis': re.compile(r'\b(redis)\b', re.IGNORECASE),
    'Cassandra': re.compile(r'\b(cassandra)\b', re.IGNORECASE),
    'Elasticsearch': re.compile(r'\b(elasticsearch|elastic)\b', re.IGNORECASE),
    'DynamoDB': re.compile(r'\b(dynamodb)\b', re.IGNORECASE),
    
    # Tools & Platforms
    'AWS': re.compile(r'\b(aws|amazon\s*web\s*services|ec2|s3)\b', re.IGNORECASE),
    'Azure': re.compile(r'\b(azure|microsoft\s*azure)\b', re.IGNORECASE),
    'GCP': re.compile(r'\b(gcp|google\s*cloud|google\s*cloud\s*platform)\b', re.IGNORECASE),
    'Docker': re.compile(r'\b(docker|containers)\b', re.IGNORECASE),
    'Kubernetes': re.compile(r'\b(kubernetes|k8s)\b', re.IGNORECASE),
    'Git': re.compile(r'\b(git|github|gitlab)\b', re.IGNORECASE),
    'Jenkins': re.compile(r'\b(jenkins)\b', re.IGNORECASE),
    'Terraform': re.compile(r'\b(terraform)\b', re.IGNORECASE),
    'CI/CD': re.compile(r'\b(ci/cd|cicd|continuous\s*integration|continuous\s*deployment)\b', re.IGNORECASE),
    'Airflow': re.compile(r'\b(airflow|apache\s*airflow)\b', re.IGNORECASE),
    'Snowflake': re.compile(r'\b(snowflake)\b', re.IGNORECASE),
    'Kafka': re.compile(r'\b(kafka|apache\s*kafka)\b', re.IGNORECASE),
    
    # Concepts & ML
    'Agile': re.compile(r'\b(agile|scrum|kanban)\b', re.IGNORECASE),
    'Machine Learning': re.compile(r'\b(machine\s*learning|ml)\b', re.IGNORECASE),
    'Deep Learning': re.compile(r'\b(deep\s*learning|dl)\b', re.IGNORECASE),
    'NLP': re.compile(r'\b(nlp|natural\s*language\s*processing)\b', re.IGNORECASE),
    'DevOps': re.compile(r'\b(devops)\b', re.IGNORECASE),
    'Microservices': re.compile(r'\b(microservices|micro-services)\b', re.IGNORECASE),
    'API': re.compile(r'\b(api|apis|restful|rest\s*api)\b', re.IGNORECASE)
}


def clean_text(raw_html: str) -> str:
    """Strips HTML tags, character entities, and excess whitespace."""
    if not raw_html or not isinstance(raw_html, str):
        return ""
    text_clean = re.sub(r'<[^>]+>', ' ', raw_html)
    text_clean = text_clean.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text_clean = text_clean.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    text_clean = re.sub(r'\s+', ' ', text_clean).strip()
    return text_clean


def extract_skills_from_text(title: str, description: str) -> list:
    """Identifies technical skills mentioned in job title and description."""
    combined_text = f"{title} {description}"
    matched = []
    
    for skill, pattern in SKILLS_PATTERNS.items():
        if skill == 'Go':
            if re.search(r'\b(golang|go\s*lang)\b', combined_text, re.IGNORECASE) or re.search(r'\bGo\b', combined_text):
                matched.append(skill)
        elif skill == 'Java':
            # Avoid matching JavaScript as Java
            if pattern.search(combined_text) and not re.search(r'\bjavascript\b', combined_text, re.IGNORECASE):
                matched.append(skill)
            elif pattern.search(combined_text):
                matched.append(skill)
        else:
            if pattern.search(combined_text):
                matched.append(skill)
                
    return list(set(matched))


def fetch_adzuna_jobs(app_id: str, app_key: str, country: str = "in", keyword: str = "software engineer", page: int = 1, results_per_page: int = 50) -> list:
    """Queries Adzuna API for job postings in a specific country."""
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": results_per_page,
        "what": keyword,
        "content-type": "application/json",
    }
    try:
        response = requests.get(url, params=params, timeout=12)
        if response.status_code == 200:
            return response.json().get("results", [])
        else:
            logger.warning(f"Adzuna API returned status {response.status_code} for {country}/{keyword} (page {page})")
            return []
    except Exception as e:
        logger.warning(f"Failed to query Adzuna for {country}/{keyword} (page {page}): {e}")
        return []


def get_db_engine():
    """Builds SQLAlchemy engine from environment variables."""
    u = os.getenv("DB_USER", "root")
    pw = os.getenv("DB_PASSWORD", "")
    h = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    d = os.getenv("DB_NAME", "skillpulse")
    return create_engine(
        f"mysql+pymysql://{u}:{quote_plus(pw)}@{h}:{port}/{d}",
        pool_pre_ping=True
    )


def sync_skills_table(engine):
    """Ensures all 47 canonical skills exist in the skills table and returns name->id map."""
    skills_data = [{"name": s} for s in SKILLS_PATTERNS.keys()]
    metadata = MetaData()
    skills_table = Table('skills', metadata, autoload_with=engine)
    
    with engine.begin() as conn:
        for item in skills_data:
            stmt = mysql_insert(skills_table).values(name=item['name'])
            stmt = stmt.on_duplicate_key_update(name=stmt.inserted.name)
            conn.execute(stmt)
            
    with engine.connect() as conn:
        df_skills = pd.read_sql("SELECT id, name FROM skills", conn)
    return dict(zip(df_skills['name'], df_skills['id']))


def ingest_live_jobs(countries=None, keywords=None, pages_per_combo=2, results_per_page=25):
    """
    Main orchestration function to fetch live jobs from Adzuna API,
    clean, deduplicate, extract skills, and persist to MySQL.
    """
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    
    if not app_id or not app_key or app_id == "your_adzuna_app_id":
        logger.warning("Adzuna API credentials missing in .env — skipping live API ingestion.")
        return {"status": "skipped", "new_postings": 0, "skill_links": 0}
        
    if countries is None:
        countries = ["in", "us", "gb"]
    if keywords is None:
        keywords = ["software engineer", "data scientist", "machine learning engineer", "backend developer"]

    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning(f"MySQL unavailable ({e}) — cannot persist ingested records to database.")
        return {"status": "db_offline", "new_postings": 0, "skill_links": 0}

    skill_to_id = sync_skills_table(engine)
    
    # Load recent postings for deduplication fingerprint
    with engine.connect() as conn:
        existing_fps = set()
        df_recent = pd.read_sql(
            "SELECT LOWER(TRIM(title)) as t, LOWER(TRIM(IFNULL(company,''))) as c, LOWER(TRIM(country)) as co, SUBSTRING(LOWER(TRIM(IFNULL(description,''))), 1, 100) as d FROM job_postings ORDER BY id DESC LIMIT 5000",
            conn
        )
        for _, r in df_recent.iterrows():
            existing_fps.add((r['t'], r['c'], r['co'], r['d']))

    all_new_postings = []
    
    logger.info(f"🚀 Starting live Adzuna ingestion across {len(countries)} countries and {len(keywords)} tech keywords...")

    for country in countries:
        country_new = 0
        for kw in keywords:
            for page in range(1, pages_per_combo + 1):
                raw_results = fetch_adzuna_jobs(app_id, app_key, country=country, keyword=kw, page=page, results_per_page=results_per_page)
                if not raw_results:
                    break
                
                for item in raw_results:
                    title = clean_text(item.get("title", ""))
                    company = clean_text(item.get("company", {}).get("display_name", ""))
                    location = clean_text(item.get("location", {}).get("display_name", ""))
                    desc = clean_text(item.get("description", ""))
                    posted_date = (item.get("created") or "")[:10] or None
                    sal_min = item.get("salary_min")
                    sal_max = item.get("salary_max")
                    
                    if not title or len(title) < 2:
                        continue
                        
                    fp = (title.lower().strip(), company.lower().strip(), country.lower().strip(), desc.lower().strip()[:100])
                    if fp in existing_fps:
                        continue
                    existing_fps.add(fp)
                    
                    matched_skills = extract_skills_from_text(title, desc)
                    
                    all_new_postings.append({
                        "source": "adzuna",
                        "country": country,
                        "title": title,
                        "company": company,
                        "location": location,
                        "salary_min": sal_min,
                        "salary_max": sal_max,
                        "description": desc,
                        "posted_date": posted_date,
                        "raw_json": json.dumps(item),
                        "_matched_skills": matched_skills
                    })
                    country_new += 1
                
                time.sleep(0.5)  # Respect API rate limits
        logger.info(f"  [{country.upper()}] Fetched {country_new} new unique job postings from Adzuna")

    if not all_new_postings:
        logger.info("No new unique job postings found from Adzuna API this run.")
        return {"status": "success", "new_postings": 0, "skill_links": 0}

    # Insert into MySQL
    inserted_count = 0
    skills_linked_count = 0

    with engine.begin() as conn:
        for posting in all_new_postings:
            matched_skills = posting.pop("_matched_skills", [])
            res = conn.execute(text("""
                INSERT INTO job_postings (source, country, title, company, location, salary_min, salary_max, description, posted_date, raw_json)
                VALUES (:source, :country, :title, :company, :location, :salary_min, :salary_max, :description, :posted_date, :raw_json)
            """), posting)
            job_id = res.lastrowid
            inserted_count += 1
            
            for sk_name in matched_skills:
                sk_id = skill_to_id.get(sk_name)
                if sk_id:
                    conn.execute(text("""
                        INSERT IGNORE INTO job_skills (job_id, skill_id)
                        VALUES (:job_id, :skill_id)
                    """), {"job_id": job_id, "skill_id": sk_id})
                    skills_linked_count += 1

    logger.info(f"✅ Ingestion complete: Inserted {inserted_count} new postings & mapped {skills_linked_count} skill links into MySQL!")
    return {
        "status": "success",
        "new_postings": inserted_count,
        "skill_links": skills_linked_count
    }


if __name__ == "__main__":
    result = ingest_live_jobs(pages_per_combo=2, results_per_page=30)
    print(json.dumps(result, indent=2))
