import streamlit as st

class UIEngine:
    @staticmethod
    def setup_page():
        """
        Injects CSS for a WIDER Sidebar and DEEPER Colors.
        """
        st.markdown("""
            <style>
                /* --- 1. GLOBAL THEME --- */
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
                
                .stApp {
                    background-color: #ffffff;
                    font-family: 'Inter', sans-serif;
                }
                
                /* --- 2. SIDEBAR CONFIGURATION --- */
                /* FORCE SIDEBAR WIDTH & COLOR */
                section[data-testid="stSidebar"] {
                    width: 300px !important; /* WIDER SIDEBAR */
                    min-width: 300px !important;
                    background-color: #0f0a1e !important; /* DEEP RICH PURPLE */
                    border-right: 1px solid #2b2638;
                }
                
                /* Sidebar Text Colors */
                [data-testid="stSidebar"] * {
                    color: #e0e7ff !important; /* Bright White-Blue Text */
                }
                
                /* --- 3. METRIC CARDS --- */
                div[data-testid="stMetric"] {
                    background-color: #ffffff;
                    border: 1px solid #e5e7eb;
                    border-radius: 12px;
                    padding: 16px;
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
                }
                
                /* --- 4. CHAT BUBBLES --- */
                .chat-user {
                    background-color: #f3f4f6;
                    color: #1f2937;
                    padding: 14px 18px;
                    border-radius: 12px 12px 0px 12px;
                    margin: 8px 0;
                    text-align: right;
                    float: right;
                    clear: both;
                    max-width: 80%;
                    font-size: 15px;
                }
                .chat-ai {
                    background-color: #ffffff;
                    color: #1f2937;
                    padding: 14px 18px;
                    border-radius: 12px 12px 12px 0px;
                    margin: 8px 0;
                    border: 1px solid #e5e7eb;
                    border-left: 4px solid #8b5cf6;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                    float: left;
                    clear: both;
                    max-width: 80%;
                    font-size: 15px;
                }
                
                /* --- 5. BUTTONS --- */
                div.stButton > button {
                    background-color: #8b5cf6;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: 600;
                    padding: 0.6rem 1.2rem;
                    font-size: 16px;
                    transition: all 0.2s;
                }
                div.stButton > button:hover {
                    background-color: #7c3aed;
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
                }
            </style>
        """, unsafe_allow_html=True)

    @staticmethod
    def render_empty_state(title="No documents yet", subtitle="Upload a file to get started"):
        st.markdown(f"""
        <div style="text-align: center; padding: 80px 20px;">
            <div style="display: inline-flex; align-items: center; justify-content: center; width: 90px; height: 90px; background-color: #f5f3ff; border-radius: 50%; margin-bottom: 24px;">
                <svg width="45" height="45" fill="none" stroke="#8b5cf6" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"></path></svg>
            </div>
            <h3 style="font-size: 1.8rem; font-weight: 700; color: #111827; margin-bottom: 10px;">{title}</h3>
            <p style="color: #6b7280; font-size: 1.1rem;">{subtitle}</p>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def render_error_toast(title, message):
        st.error(f"**{title}**: {message}")