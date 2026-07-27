SIDEBAR_STYLES = {
    "container": {"padding": "1.5rem 0", "background-color": "#f8fafc", "border-right": "1px solid #e2e8f0"},
    "icon": {"color": "#0ea5e9", "font-size": "20px"},
    "nav-link": {"font-size": "14px", "text-align": "left", "padding": "10px 24px", "color": "#475569", "border-left": "2px solid transparent", "letter-spacing": "0.3px"},
    "nav-link-selected": {"background-color": "rgba(14,165,233,0.08)", "color": "#0ea5e9", "border-left": "2px solid #0ea5e9", "font-weight": "500"}
}

HIDE_SIDEBAR_NAV = """
<style>
    /* Hide the default multi-page navigation */
    [data-testid="stSidebarNav"] {
        display: none;
    }
    
    /* Make the custom sidebar navigation more prominent */
    .sidebar .sidebar-content {
        padding-top: 2rem;
    }
</style>
"""

TEXT_JUSTIFIED = """
<style>
    .justified-text {
        text-align: justify;
        text-justify: inter-word;
    }
    
    /* Apply to all Streamlit markdown */
    .stMarkdown {
        text-align: justify;
    }
</style>
"""

INFO_BOX_STYLES = """
<style>
    .cool-info {
        background: #f0f7ff;
        padding: 20px 24px;
        border-radius: 12px;
        border-left: 5px solid #0ea5e9;
        margin: 12px 0;
    }
    
    .cool-info h4 {
        margin: 0 0 8px 0;
        color: #0c4a6e;
    }
    
    .cool-info p {
        margin: 0;
        color: #1e293b;
        line-height: 1.7;
    }
    
    .cool-info .highlight {
        color: #0ea5e9;
        font-weight: 600;
        display: block;
        margin-top: 8px;
    }
</style>
"""

METRICS_BOX_STYLE ="""
    <style>
        /* Smaller metric labels */
        div[data-testid="metric-container"] {
            width: 100%;
        }
        div[data-testid="metric-container"] label {
            font-size: 12px !important;
        }
        div[data-testid="metric-container"] div[data-testid="metric-value"] {
            font-size: 18px !important;
        }
    </style>
"""