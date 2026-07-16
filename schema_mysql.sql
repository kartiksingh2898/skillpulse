-- SkillPulse Database Schema (MySQL)
-- Run this in MySQL Workbench: open a new SQL tab, paste, and execute (the lightning bolt icon)

CREATE DATABASE IF NOT EXISTS skillpulse;
USE skillpulse;

CREATE TABLE job_postings (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    source         VARCHAR(50),          -- 'adzuna', 'remoteok', etc.
    title          VARCHAR(255),
    company        VARCHAR(255),
    location       VARCHAR(255),
    salary_min     DECIMAL(12,2),
    salary_max     DECIMAL(12,2),
    description    TEXT,
    posted_date    DATE,
    scraped_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    raw_json       JSON                  -- keep the original API response, cheap insurance
);

CREATE TABLE skills (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    name           VARCHAR(100) UNIQUE
);

CREATE TABLE job_skills (
    job_id         INT,
    skill_id       INT,
    PRIMARY KEY (job_id, skill_id),
    FOREIGN KEY (job_id) REFERENCES job_postings(id),
    FOREIGN KEY (skill_id) REFERENCES skills(id)
);

CREATE TABLE model_runs (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    trained_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    model_type     VARCHAR(50),          -- 'linear_regression', 'xgboost'
    mae            DECIMAL(12,4),
    rmse           DECIMAL(12,4),
    notes          TEXT
);

CREATE TABLE drift_reports (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    run_date            DATETIME DEFAULT CURRENT_TIMESTAMP,
    feature_drift_pct   DECIMAL(8,4) DEFAULT NULL,    -- % of features that drifted
    target_drift        TINYINT(1)   DEFAULT 0,        -- 1 if target distribution drifted
    alert_triggered     TINYINT(1)   DEFAULT 0,        -- 1 if threshold exceeded
    report_json         JSON                           -- full evidently summary JSON
);
