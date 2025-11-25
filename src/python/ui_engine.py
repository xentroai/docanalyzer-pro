import streamlit as st

class UIEngine:
    @staticmethod
    def setup_page():
        """
        Injects reliable Custom CSS (No external script dependency).
        """
        st.markdown("""
            <style>
                /* 1. APP BACKGROUND & FONT */
                .stApp {
                    background-color: #0e1117;
                    font-family: 'Inter', sans-serif;
                }
                
                /* 2. CARD STYLING (The Metrics) */
                .kpi-card {
                    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                    border: 1px solid #334155;
                    border-radius: 12px;
                    padding: 20px;
                    margin-bottom: 15px;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                    transition: transform 0.2s;
                }
                .kpi-card:hover {
                    transform: translateY(-5px);
                    border-color: #60a5fa;
                }
                .kpi-title {
                    color: #94a3b8;
                    font-size: 0.8rem;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    font-weight: 600;
                }
                .kpi-value {
                    color: #ffffff;
                    font-size: 1.8rem;
                    font-weight: 700;
                    margin: 8px 0;
                }
                .kpi-sub {
                    font-size: 0.75rem;
                    color: #64748b;
                }

                /* 3. EMPTY STATE (Fixing the Giant Cloud Bug) */
                .empty-state-container {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    padding: 40px;
                    background-color: rgba(30, 41, 59, 0.5);
                    border: 2px dashed #475569;
                    border-radius: 16px;
                    margin-top: 20px;
                    text-align: center;
                }
                .empty-icon {
                    width: 64px;  /* FORCE SIZE */
                    height: 64px; /* FORCE SIZE */
                    color: #60a5fa;
                    margin-bottom: 20px;
                }
                .empty-title {
                    color: white;
                    font-size: 1.25rem;
                    font-weight: 600;
                    margin-bottom: 8px;
                }
                .empty-desc {
                    color: #94a3b8;
                    font-size: 0.9rem;
                    max-width: 300px;
                }

                /* 4. ERROR TOAST */
                .error-box {
                    background-color: #450a0a;
                    border-left: 4px solid #ef4444;
                    padding: 16px;
                    border-radius: 0 8px 8px 0;
                    margin-bottom: 16px;
                }
                .error-title {
                    color: #fca5a5;
                    font-weight: 600;
                    font-size: 0.9rem;
                }
                .error-msg {
                    color: #fee2e2;
                    font-size: 0.85rem;
                    margin-top: 4px;
                }
            </style>
        """, unsafe_allow_html=True)

    @staticmethod
    def styled_card(title, value, subtext, icon="📊", color="blue"):
        """
        Renders a metric card using the CSS classes above.
        """
        html = f"""
        <div class="kpi-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="kpi-title">{title}</span>
                <span style="font-size: 1.5rem;">{icon}</span>
            </div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{subtext}</div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)

    @staticmethod
    def render_empty_state():
        """
        Renders the upload prompt with a FIXED SIZE icon.
        """
        html = """
        <div class="empty-state-container">
            <svg class="empty-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" width="64" height="64">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
            </svg>
            <div class="empty-title">Ready for Analysis</div>
            <div class="empty-desc">
                Upload a document to activate the Neural Engine.
                <br>Supported: PDF, JPG, PNG
            </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)

    @staticmethod
    def render_error_toast(title, message, details=None):
        """
        Renders a red error box.
        """
        detail_html = f'<div style="margin-top:8px; font-family:monospace; font-size:0.75rem; color:#fecaca;">{details}</div>' if details else ''
        
        html = f"""
        <div class="error-box">
            <div class="error-title">{title}</div>
            <div class="error-msg">{message}</div>
            {detail_html}
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)