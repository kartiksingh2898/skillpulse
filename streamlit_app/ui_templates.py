def render_metric_card(label: str, value: str, sub_text: str) -> str:
    """Returns HTML for a glassmorphism metric card."""
    return f"""
    <div class="glass-panel metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{sub_text}</div>
    </div>
    """

def render_job_card(title: str, company: str, location: str, salary_str: str, 
                    posted: str, description: str, apply_url: str, apply_label: str) -> str:
    """Returns HTML for a glassmorphism job card."""
    return f"""
    <div class="glass-panel job-card">
        <div style="font-size: 12px; color: var(--text-muted); float: right;">📅 {posted}</div>
        <a class="job-title" href="{apply_url}" target="_blank">{title}</a><br>
        <span class="job-company">🏢 {company}</span>
        <span class="job-location">📍 {location}</span><br>
        <div style="margin-top: 8px; margin-bottom: 8px;">
            <span class="success-pill">💰 {salary_str}</span>
        </div>
        <div class="job-desc">{description}</div>
        <div style="margin-top: 16px; text-align: right;">
            <a href="{apply_url}" target="_blank" style="
                background: var(--accent-primary);
                color: white; font-weight: 700; font-size: 13px; padding: 10px 20px;
                border-radius: 8px; text-decoration: none; display: inline-block;
                box-shadow: var(--shadow-sm); transition: transform 0.2s, box-shadow 0.2s;
            ">{apply_label}</a>
        </div>
    </div>
    """

def render_info_banner(icon: str, text: str) -> str:
    """Returns HTML for an information banner."""
    return f"""
    <div class="info-banner">
        {icon} {text}
    </div>
    """

def render_section_badge(text: str) -> str:
    """Returns HTML for a small section badge."""
    return f'<div class="stack-pill" style="margin-bottom: 12px;">{text}</div>'
    
def render_page_title(icon: str, text: str) -> str:
    """Returns HTML for a page title with gradient text."""
    return f"""
    <div class="page-title" style="font-size: 28px; font-weight: 800; display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
        <span>{icon}</span>
        <span class="gradient-text">{text}</span>
    </div>
    """
