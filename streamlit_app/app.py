import os
import json
import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from urllib.parse import quote_plus

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SkillPulse — Live Job Market Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Premium CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Sidebar Styling */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #090d16 0%, #0f172a 100%);
    border-right: 1px solid #1e293b;
}
section[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}

/* Main Background */
.stApp {
    background-color: #0b0f19;
    color: #f1f5f9;
}

/* Card layout */
.metric-card {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.25);
    text-align: center;
}
.metric-card .label {
    font-size: 11px;
    color: #9ca3af;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
.metric-card .value {
    font-size: 32px;
    font-weight: 800;
    color: #0d9488;
    margin-top: 6px;
}

/* Custom Predictions Card */
.prediction-card {
    background: linear-gradient(135deg, #0d9488 0%, #0f766e 50%, #115e59 100%);
    border-radius: 16px;
    padding: 30px;
    box-shadow: 0 10px 30px rgba(13, 148, 136, 0.25);
    text-align: center;
    border: 1px solid rgba(255, 255, 255, 0.1);
}
.prediction-card .val {
    font-size: 54px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.02em;
}
.prediction-card .sub-val {
    font-size: 16px;
    color: #ccfbf1;
    margin-top: 5px;
    font-weight: 500;
}

/* Style Selectors & Inputs */
div[data-baseweb="select"] {
    background-color: #111827 !important;
    border: 1px solid #1f2937 !important;
    border-radius: 8px !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #0d9488 0%, #0d9488 100%) !important;
    color: white !important;
    font-weight: 700 !important;
    border: none !important;
    padding: 12px 30px !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 15px rgba(13, 148, 136, 0.4) !important;
    transition: all 0.2s ease-in-out;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(13, 148, 136, 0.6) !important;
}

/* Table container styling */
.stDataFrame {
    border: 1px solid #1f2937;
    border-radius: 10px;
    background: #0f172a;
}
</style>
""", unsafe_allow_html=True)

# ── Plotly Custom Dark Style ──────────────────────────────────────────────────
PLOTLY_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#9ca3af", family="Inter"),
    xaxis=dict(gridcolor="#1f2937", zeroline=False, tickfont=dict(color="#9ca3af")),
    yaxis=dict(gridcolor="#1f2937", zeroline=False, tickfont=dict(color="#9ca3af")),
)

# ── DB & Model Connection Caching ─────────────────────────────────────────────
load_dotenv(dotenv_path=".env")

@st.cache_resource
def get_db_engine():
    return create_engine(
        f"mysql+pymysql://{os.getenv('DB_USER')}:{quote_plus(os.getenv('DB_PASSWORD'))}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}",
        pool_pre_ping=True
    )

@st.cache_resource
def get_prediction_model():
    model = joblib.load("models/xgboost_model.joblib")
    with open("data_exports/feature_names.json", "r") as f:
        feature_names = json.load(f)
    return model, feature_names

try:
    engine = get_db_engine()
    model, FEATURE_NAMES = get_prediction_model()
except Exception as e:
    st.error(f"Failed to connect to the database or load the ML model: {e}")
    st.stop()

# ── Database Query Helper ─────────────────────────────────────────────────────
def run_query(sql, params=None):
    with engine.connect() as conn:
        res = conn.execute(text(sql), params or {})
        return pd.DataFrame(res.fetchall(), columns=res.keys())

# ── Sidebar Navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h2 style='color:#0d9488;'>⚡ SkillPulse</h2>", unsafe_allow_html=True)
    st.markdown("🌐 **MLOps Market Analytics Portal**")
    st.markdown("---")
    menu = st.radio(
        "Choose Dashboard View",
        ["🏠 Market Overview", "📊 Skill Intelligence", "💰 Salary Predictor", "⚙️ Model Diagnostics"]
    )
    st.markdown("---")
    st.caption("Active Stack:")
    st.caption("• XGBoost Regressor")
    st.caption("• Optuna Hyper-Tuning")
    st.caption("• MySQL Database Store")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1: MARKET OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
if menu == "🏠 Market Overview":
    st.markdown("# 🏠 Job Market Overview")
    st.markdown("Real-time telemetry and database ingestion statistics.")
    st.markdown("---")

    # Ingested counts
    stats = run_query("""
        SELECT 
            (SELECT COUNT(*) FROM job_postings) AS total_rows,
            (SELECT COUNT(*) FROM job_skills) AS total_mappings,
            (SELECT COUNT(*) FROM skills) AS total_skills,
            (SELECT COUNT(*) FROM model_runs) AS total_runs
    """).iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="label">Total Job Postings</div><div class="value">{stats["total_rows"]:,}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="label">Skills Mapped</div><div class="value">{stats["total_mappings"]:,}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="label">Tracked Tech Skills</div><div class="value">{stats["total_skills"]}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card"><div class="label">ML Model Runs</div><div class="value">{stats["total_runs"]}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🌎 Distribution of Postings by Country")
        country_data = run_query("""
            SELECT country, COUNT(*) AS count 
            FROM job_postings 
            GROUP BY country
        """)
        country_data["Country Name"] = country_data["country"].map({"us": "United States", "gb": "United Kingdom", "in": "India"})
        
        fig = px.pie(
            country_data, values="count", names="Country Name",
            color_discrete_sequence=["#f59e0b", "#818cf8", "#0d9488"],
            hole=0.4
        )
        fig.update_layout(**PLOTLY_THEME, height=320, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 💵 Salary Data Transparency Profile")
        transparency = run_query("""
            SELECT country,
                   COUNT(*) AS total,
                   SUM(CASE WHEN salary_min IS NOT NULL THEN 1 ELSE 0 END) AS populated
            FROM job_postings
            GROUP BY country
        """)
        transparency["Country Name"] = transparency["country"].map({"us": "United States", "gb": "United Kingdom", "in": "India"})
        # Cast columns to float to ensure compatibility with .round() across all pandas/numpy versions
        transparency["populated"] = transparency["populated"].astype(float)
        transparency["total"] = transparency["total"].astype(float)
        transparency["Coverage %"] = (transparency["populated"] / transparency["total"] * 100).round(1)

        fig2 = px.bar(
            transparency, x="Country Name", y="Coverage %",
            color="Country Name",
            color_discrete_map={"United States": "#f59e0b", "United Kingdom": "#818cf8", "India": "#0d9488"},
            labels={"Coverage %": "Coverage (%)"}
        )
        fig2.update_layout(**PLOTLY_THEME, showlegend=False, height=320, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.markdown("### 🏢 Top 10 Hiring Companies")
    top_cos = run_query("""
        SELECT company AS Company, COUNT(*) AS `Open Postings`
        FROM job_postings
        WHERE company IS NOT NULL AND company != ''
        GROUP BY company
        ORDER BY `Open Postings` DESC
        LIMIT 10
    """)
    st.dataframe(top_cos, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2: SKILL INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "📊 Skill Intelligence":
    st.markdown("# 📊 Skill Demand Intelligence")
    st.markdown("Deep analytical tracking of technology profiles and skill correlation frameworks.")
    st.markdown("---")

    # Select country for detailed skill breakdown
    selected_country = st.selectbox("Filter Country Focus", ["United States", "United Kingdom", "India"])
    country_code = {"United States": "us", "United Kingdom": "gb", "India": "in"}[selected_country]

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown(f"### 🔥 Top 15 Technologies in {selected_country}")
        top_skills = run_query("""
            SELECT s.name AS Skill, COUNT(js.job_id) AS Mentions
            FROM skills s
            JOIN job_skills js ON js.skill_id = s.id
            JOIN job_postings jp ON jp.id = js.job_id
            WHERE jp.country = :country
            GROUP BY s.name
            ORDER BY Mentions DESC
            LIMIT 15
        """, {"country": country_code})

        fig = px.bar(
            top_skills, x="Mentions", y="Skill", orientation="h",
            color="Mentions", color_continuous_scale="Viridis",
            labels={"Mentions": "Count of Mentions", "Skill": ""}
        )
        fig.update_layout(**PLOTLY_THEME, height=450, coloraxis_showscale=False, margin=dict(l=10, r=10, t=10, b=10))
        fig.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 🔗 Co-occurring Skill Network Explorer")
        st.caption("Select a skill to view which other technologies frequently appear alongside it in job descriptions.")
        
        # Pull all distinct skill names
        all_skills_list = run_query("SELECT name FROM skills ORDER BY name")["name"].tolist()
        base_skill = st.selectbox("Select Target Skill", all_skills_list, index=all_skills_list.index("Python") if "Python" in all_skills_list else 0)

        related_skills = run_query("""
            SELECT s2.name AS Skill, COUNT(*) AS CoOccurrences
            FROM job_skills js1
            JOIN job_skills js2 ON js1.job_id = js2.job_id
            JOIN skills s1 ON s1.id = js1.skill_id
            JOIN skills s2 ON s2.id = js2.skill_id
            WHERE s1.name = :skill AND s2.name != :skill
            GROUP BY s2.name
            ORDER BY CoOccurrences DESC
            LIMIT 8
        """, {"skill": base_skill})

        if related_skills.empty:
            st.info("No co-occurring skills found for this selection.")
        else:
            fig3 = px.bar(
                related_skills, x="CoOccurrences", y="Skill", orientation="h",
                color_discrete_sequence=["#0d9488"],
                labels={"CoOccurrences": "Co-occurrence Matches", "Skill": ""}
            )
            fig3.update_layout(**PLOTLY_THEME, height=350, margin=dict(l=10, r=10, t=10, b=10))
            fig3.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")
    st.markdown("### 💰 High-Value Tech Skills (US & UK)")
    st.caption("Average salary baseline (in USD) associated with specific skill mentions across jobs containing salary information.")
    
    val_skills = run_query("""
        SELECT s.name AS Skill,
               ROUND(AVG((jp.salary_min + jp.salary_max) / 2 * CASE WHEN jp.country = 'gb' THEN 1.27 ELSE 1.0 END), 2) AS `Average Salary (USD)`,
               COUNT(jp.id) AS `Sample Size`
        FROM skills s
        JOIN job_skills js ON js.skill_id = s.id
        JOIN job_postings jp ON jp.id = js.job_id
        WHERE jp.salary_min IS NOT NULL AND jp.salary_max IS NOT NULL AND jp.country IN ('us', 'gb')
        GROUP BY s.name
        HAVING `Sample Size` >= 10
        ORDER BY `Average Salary (USD)` DESC
        LIMIT 15
    """)
    
    if not val_skills.empty:
        fig4 = px.bar(
            val_skills, x="Skill", y="Average Salary (USD)",
            color="Average Salary (USD)", color_continuous_scale="Cividis",
            labels={"Average Salary (USD)": "Salary (USD)"}
        )
        fig4.update_layout(**PLOTLY_THEME, height=380, coloraxis_showscale=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("Insufficient salary-populated mappings to generate valuation charts.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3: SALARY PREDICTOR & MATCHING JOBS
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "💰 Salary Predictor":
    st.markdown("# 💰 Salary Prediction Engine")
    st.markdown("Estimate candidate valuations using our optimized XGBoost model and scan matching live listings.")
    st.markdown("---")

    # Get skill items that are in feature names list
    model_skills = sorted([col for col in FEATURE_NAMES if col not in ["country_gb", "country_us"]])

    col1, col2 = st.columns([3, 1])
    with col1:
        user_skills = st.multiselect(
            "🛠️ Select Technology Competencies",
            options=model_skills,
            default=["Python", "AWS", "SQL"] if "Python" in model_skills else []
        )
    with col2:
        user_country = st.selectbox("🌍 Target Geography", ["United States (USD)", "United Kingdom (GBP)"])

    country_key = "us" if "United States" in user_country else "gb"

    st.markdown("")
    if st.button("🔮 Calculate Salary & Scan Postings"):
        if not user_skills:
            st.warning("Please select at least one technology competence feature.")
        else:
            # Build feature array for prediction
            skills_lower = {s.lower() for s in user_skills}
            fv = []
            for col in FEATURE_NAMES:
                if col == "country_gb":
                    fv.append(1 if country_key == "gb" else 0)
                elif col == "country_us":
                    fv.append(1 if country_key == "us" else 0)
                else:
                    fv.append(1 if col.lower() in skills_lower else 0)

            # Predict
            pred_log = float(model.predict(np.array([fv], dtype=np.float32))[0])
            pred_usd = float(np.expm1(pred_log))

            if country_key == "gb":
                pred_local = pred_usd / 1.27
                local_symbol = "£"
                local_suffix = "GBP"
            else:
                pred_local = pred_usd
                local_symbol = "$"
                local_suffix = "USD"

            # Display card
            st.markdown(f"""
                <div class="prediction-card">
                    <div class="label" style="color:rgba(255,255,255,0.7)">Projected Salary Base Valuation</div>
                    <div class="val">{local_symbol}{pred_local:,.2f} {local_suffix}</div>
                    <div class="sub-val">Equivalent to ${pred_usd:,.2f} USD</div>
                </div>
            """, unsafe_allow_html=True)

            # Display gauges
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number",
                value=pred_local,
                number={"prefix": local_symbol, "font": {"size": 38, "color": "#0d9488"}},
                gauge={
                    "axis": {"range": [30000, 220000], "tickcolor": "#9ca3af"},
                    "bar": {"color": "#0d9488"},
                    "bgcolor": "#111827",
                    "bordercolor": "#1f2937",
                    "steps": [
                        {"range": [30000, 90000], "color": "#1f2937"},
                        {"range": [90000, 150000], "color": "#111827"},
                        {"range": [150000, 220000], "color": "#032b26"}
                    ]
                }
            ))
            fig_g.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e5e7eb", height=240, margin=dict(t=10, b=10))
            st.plotly_chart(fig_g, use_container_width=True)

            # Fetch matching jobs from the database
            st.markdown("---")
            st.markdown("### 🏢 Matching Job Openings in Database")
            st.caption("Live postings in the database that mention one or more of your selected tech skills:")

            placeholders = ", ".join(f":skill_{i}" for i in range(len(user_skills)))
            query_params = {f"skill_{i}": s for i, s in enumerate(user_skills)}
            query_params["country"] = country_key

            matching_jobs = run_query(f"""
                SELECT jp.title AS Title, jp.company AS Company, jp.location AS Location,
                       CONCAT(jp.salary_min, ' - ', jp.salary_max) AS `Salary Range`,
                       jp.description AS Description
                FROM job_postings jp
                JOIN job_skills js ON js.job_id = jp.id
                JOIN skills s ON s.id = js.skill_id
                WHERE s.name IN ({placeholders}) AND jp.country = :country
                GROUP BY jp.id
                ORDER BY jp.id DESC
                LIMIT 10
            """, query_params)

            if matching_jobs.empty:
                st.info("No active jobs matching these parameters were found in the database.")
            else:
                st.dataframe(matching_jobs, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4: MODEL DIAGNOSTICS & HISTORY
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "⚙️ Model Diagnostics":
    st.markdown("# ⚙️ Model Diagnostics & MLOps Runs")
    st.markdown("Governance records, parameter footprints, and feature relevance indicators.")
    st.markdown("---")

    # DB records
    runs = run_query("""
        SELECT id AS RunID, trained_at AS `Trained At`, model_type AS Type,
               ROUND(mae, 4) AS `Log MAE`, ROUND(rmse, 4) AS `Log RMSE`, notes
        FROM model_runs
        ORDER BY trained_at DESC
    """)

    if runs.empty:
        st.info("No run telemetry logged inside target database tables yet.")
    else:
        # Diagnostic summary
        best_run_idx = runs["Log RMSE"].idxmin()
        best_run = runs.loc[best_run_idx]

        c1, c2, c3 = st.columns(3)
        c1.metric("Governance Database Record Count", len(runs))
        c2.metric("Best Log Validation MAE", best_run["Log MAE"])
        c3.metric("Best Log Validation RMSE", best_run["Log RMSE"])

        st.markdown("---")
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("### 🪵 Historical Training Runs")
            st.dataframe(
                runs[["RunID", "Trained At", "Type", "Log MAE", "Log RMSE"]],
                use_container_width=True,
                hide_index=True
            )

        with col2:
            st.markdown("### 🏆 Optimal XGBoost Parameters")
            try:
                run_notes = json.loads(best_run["notes"])
                opt_params = run_notes.get("best_params", {})
                opt_r2 = run_notes.get("r2", "N/A")
                opt_raw_mae = run_notes.get("raw_mae_usd", "N/A")

                st.markdown(f"**Optimization R² Score:** `{opt_r2}`")
                st.markdown(f"**Mean Absolute Error (USD):** `${opt_raw_mae:,.2f}`")
                
                params_df = pd.DataFrame(opt_params.items(), columns=["Hyperparameter", "Value"])
                st.dataframe(params_df, use_container_width=True, hide_index=True)
            except Exception:
                st.code(best_run["notes"])

        # Display Feature importance
        st.markdown("---")
        st.markdown("### 📊 Tuned Estimator Feature Relevance")
        st.caption("Relative weight of variables inside the final trained regressor.")

        feat_imps = model.feature_importances_
        importance_df = pd.DataFrame({
            "Feature": FEATURE_NAMES,
            "Importance": feat_imps
        }).sort_values(by="Importance", ascending=False).head(15)

        fig_imp = px.bar(
            importance_df, x="Importance", y="Feature", orientation="h",
            color="Importance", color_continuous_scale="Teal",
            labels={"Importance": "Relevance Score", "Feature": ""}
        )
        fig_imp.update_layout(**PLOTLY_THEME, height=400, coloraxis_showscale=False, margin=dict(l=10, r=10, t=10, b=10))
        fig_imp.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig_imp, use_container_width=True)
