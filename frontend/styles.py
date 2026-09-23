"""Custom CSS styles for the Multi-Agent Research Assistant frontend."""


def get_custom_css() -> str:
    """Return custom CSS for the Streamlit app, supporting both dark and light themes."""
    return """
    <style>
    /* App shell — white background */
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"],
    .main {
        background-color: #ffffff !important;
    }

    /* Global typography and spacing */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
        background-color: #ffffff;
    }

    /* Sidebar — force light panel (overrides Streamlit dark theme) */
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] > div,
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
    .stApp[data-theme="dark"] section[data-testid="stSidebar"],
    .stApp[data-theme="dark"] section[data-testid="stSidebar"] > div {
        background-color: #ffffff !important;
        background-image: none !important;
    }
    section[data-testid="stSidebar"] {
        border-right: 1px solid #e2e8f0;
        box-shadow: 2px 0 12px rgba(15, 23, 42, 0.04);
    }
    /* All sidebar copy — dark text on white */
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] small,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] div,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong,
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label,
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label p,
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label div,
    section[data-testid="stSidebar"] [data-baseweb="radio"] {
        color: #1e293b !important;
        -webkit-text-fill-color: #1e293b !important;
    }
    section[data-testid="stSidebar"] .stRadio > label {
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        font-size: 0.75rem !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 600;
    }
    section[data-testid="stSidebar"] hr {
        border: none;
        height: 1px;
        background: #e2e8f0;
        margin: 1rem 0;
    }
    section[data-testid="stSidebar"] .stButton > button {
        background: #ffffff !important;
        color: #0f766e !important;
        border: 1px solid #0d9488 !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 0.55rem 1rem !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #f0fdfa !important;
        border-color: #0f766e !important;
        color: #115e59 !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] > div {
        background-color: #ffffff !important;
        border-color: #cbd5e1 !important;
        color: #0f172a !important;
    }

    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 0.25rem 0 1.25rem 0;
        border-bottom: 1px solid #f1f5f9;
        margin-bottom: 0.75rem;
    }
    .sidebar-logo {
        font-size: 1.75rem;
        line-height: 1;
    }
    section[data-testid="stSidebar"] .sidebar-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        letter-spacing: -0.02em;
    }
    section[data-testid="stSidebar"] .sidebar-sub {
        font-size: 0.78rem;
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        margin-top: 2px;
    }
    section[data-testid="stSidebar"] .sidebar-section-label {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #0d9488 !important;
        -webkit-text-fill-color: #0d9488 !important;
        margin: 0 0 0.5rem 0;
    }
    section[data-testid="stSidebar"] .sidebar-info-card {
        background: #f8fafc !important;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem 1.1rem;
        margin: 0.5rem 0 1rem 0;
        font-size: 0.84rem;
        line-height: 1.55;
        color: #475569 !important;
        -webkit-text-fill-color: #475569 !important;
    }
    section[data-testid="stSidebar"] .sidebar-info-card strong {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        font-weight: 600;
    }
    .sidebar-info-card .tag {
        display: inline-block;
        background: #e2e8f0;
        border-radius: 6px;
        padding: 0.1rem 0.45rem;
        font-size: 0.75rem;
        font-family: ui-monospace, monospace;
        margin: 0.15rem 0;
        color: #334155;
    }
    section[data-testid="stSidebar"] .sidebar-footer {
        font-size: 0.78rem;
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        line-height: 1.5;
        border-top: 1px solid #f1f5f9;
        padding-top: 1rem;
        margin-top: 0.5rem;
    }
    section[data-testid="stSidebar"] .sidebar-footer a {
        color: #0d9488 !important;
        -webkit-text-fill-color: #0d9488 !important;
        text-decoration: none;
        font-weight: 500;
    }
    .sidebar-footer a:hover {
        text-decoration: underline;
    }
    section[data-testid="stSidebar"] .sidebar-status {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 999px;
        padding: 4px 10px;
        font-size: 0.75rem;
        color: #166534 !important;
        -webkit-text-fill-color: #166534 !important;
        margin-bottom: 0.5rem;
    }
    .sidebar-status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #34d399;
        box-shadow: 0 0 6px #34d399;
    }

    /* Card containers */
    .card-container {
        background: var(--background-color, #ffffff);
        border: 1px solid var(--border-color, #e0e0e0);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        transition: box-shadow 0.2s ease;
    }
    .card-container:hover {
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
    }

    /* Status indicators */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.3px;
    }
    .status-completed {
        background: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    .status-running {
        background: #cce5ff;
        color: #004085;
        border: 1px solid #b8daff;
        animation: pulse 1.5s ease-in-out infinite;
    }
    .status-pending {
        background: #e2e3e5;
        color: #383d41;
        border: 1px solid #d6d8db;
    }
    .status-failed {
        background: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }

    /* Agent workflow nodes */
    .agent-node {
        text-align: center;
        padding: 1rem 0.5rem;
        border-radius: 10px;
        border: 2px solid transparent;
        transition: all 0.3s ease;
    }
    .agent-node-completed {
        border-color: #28a745;
        background: rgba(40, 167, 69, 0.05);
    }
    .agent-node-running {
        border-color: #007bff;
        background: rgba(0, 123, 255, 0.05);
        animation: pulse 1.5s ease-in-out infinite;
    }
    .agent-node-pending {
        border-color: #6c757d;
        background: rgba(108, 117, 125, 0.03);
    }
    .agent-node-failed {
        border-color: #dc3545;
        background: rgba(220, 53, 69, 0.05);
    }

    .agent-icon {
        font-size: 1.8rem;
        margin-bottom: 0.3rem;
    }
    .agent-name {
        font-weight: 600;
        font-size: 0.85rem;
        margin-bottom: 0.2rem;
    }
    .agent-time {
        font-size: 0.7rem;
        color: #6c757d;
    }

    /* Arrow connectors */
    .arrow-connector {
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        color: #6c757d;
        padding-top: 1.5rem;
    }

    /* Report container */
    .report-container {
        background: var(--background-color, #ffffff);
        border: 1px solid var(--border-color, #e0e0e0);
        border-radius: 12px;
        padding: 2rem;
        line-height: 1.7;
    }

    /* Summary highlight box */
    .summary-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin: 1rem 0;
        font-size: 1.05rem;
        line-height: 1.6;
    }

    /* Search answer box */
    .answer-box {
        background: linear-gradient(135deg, #0f766e 0%, #0891b2 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin: 1rem 0 1.5rem 0;
        font-size: 1.05rem;
        line-height: 1.7;
    }

    /* Chat header */
    .chat-header {
        text-align: center;
        padding: 1.25rem 1.5rem 1.5rem 1.5rem;
        margin-bottom: 0.75rem;
        border-radius: 16px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #fff;
        box-shadow: 0 8px 24px rgba(102, 126, 234, 0.25);
    }
    .chat-header h1 {
        font-size: 1.85rem;
        font-weight: 700;
        margin-bottom: 0.35rem;
        color: #fff;
    }
    .chat-header p {
        color: rgba(255, 255, 255, 0.92);
        font-size: 0.98rem;
        margin: 0;
        max-width: 640px;
        margin-left: auto;
        margin-right: auto;
    }
    .chat-header-research {
        background: linear-gradient(135deg, #0f766e 0%, #0369a1 50%, #4338ca 100%);
        box-shadow: 0 8px 28px rgba(15, 118, 110, 0.28);
    }

    /* Full research report panel */
    .research-report-panel {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1.75rem 2rem;
        margin: 0.75rem 0 1.25rem 0;
        line-height: 1.75;
        font-size: 1rem;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
    }
    .source-card {
        background: #fff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        font-size: 0.85rem;
        transition: border-color 0.2s, box-shadow 0.2s;
    }
    .source-card:hover {
        border-color: #667eea;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.12);
    }
    .source-card a {
        color: #4338ca;
        text-decoration: none;
        font-weight: 500;
    }
    .source-card a:hover {
        text-decoration: underline;
    }

    /* Streamlit chat styling */
    [data-testid="stChatMessage"] {
        max-width: 800px;
        margin: 0 auto;
    }
    [data-testid="stChatInput"] {
        max-width: 800px;
        margin: 0 auto;
    }

    /* Citation items */
    .citation-item {
        padding: 0.8rem 1rem;
        border-left: 3px solid #667eea;
        margin-bottom: 0.8rem;
        background: rgba(102, 126, 234, 0.03);
        border-radius: 0 8px 8px 0;
    }
    .citation-item a {
        color: #667eea;
        text-decoration: none;
        font-weight: 500;
    }
    .citation-item a:hover {
        text-decoration: underline;
    }

    /* History cards */
    .history-card {
        background: var(--background-color, #ffffff);
        border: 1px solid var(--border-color, #e0e0e0);
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 0.8rem;
        transition: all 0.2s ease;
    }
    .history-card:hover {
        border-color: #667eea;
        box-shadow: 0 2px 12px rgba(102, 126, 234, 0.15);
    }

    /* Health indicator */
    .health-indicator {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .health-online {
        background: #d4edda;
        color: #155724;
    }
    .health-offline {
        background: #f8d7da;
        color: #721c24;
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #2d3748;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #718096;
        margin-top: 0.3rem;
    }

    /* Button styling */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
    }

    /* Loading state */
    .loading-container {
        text-align: center;
        padding: 2rem;
    }

    /* Mermaid code block */
    .mermaid-container {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 10px;
        padding: 1.5rem;
        overflow-x: auto;
    }

    /* Dark theme adjustments */
    @media (prefers-color-scheme: dark) {
        .card-container, .history-card {
            background: #1e1e2e;
            border-color: #313244;
        }
        .metric-card {
            background: linear-gradient(135deg, #1e1e2e 0%, #313244 100%);
        }
        .metric-value {
            color: #cdd6f4;
        }
        .metric-label {
            color: #a6adc8;
        }
        .mermaid-container {
            background: #1e1e2e;
            border-color: #313244;
        }
        .status-completed {
            background: #1e3a2e;
            color: #a3e4b8;
            border-color: #2d5a3f;
        }
        .status-running {
            background: #1e2d4a;
            color: #a3c9e4;
            border-color: #2d4a6f;
        }
        .status-pending {
            background: #2d2d3d;
            color: #a6adc8;
            border-color: #3d3d4d;
        }
        .status-failed {
            background: #3a1e1e;
            color: #e4a3a3;
            border-color: #5a2d2d;
        }
    }
    </style>
    """
