import streamlit as st
import pandas as pd
import os
import json
import time
import hashlib
import subprocess
import psutil
import re
from datetime import datetime
from llm_engine import DocumentBrain
from db_engine import DatabaseEngine
from ui_engine import UIEngine
from streamlit_option_menu import option_menu

# 1. CONFIG
st.set_page_config(page_title="Xentro Workspace", page_icon="⚡", layout="wide")
UIEngine.setup_page()

# 2. SESSION STATE
if 'page' not in st.session_state: st.session_state['page'] = "Documents"
if 'chat_history' not in st.session_state: st.session_state['chat_history'] = []
if 'active_filename' not in st.session_state: st.session_state['active_filename'] = None

# --- HELPERS ---
def get_file_hash(file_bytes):
    return hashlib.md5(file_bytes).hexdigest()

def safe_float(val):
    if val is None: return 0.0
    try:
        clean_str = str(val).replace('$', '').replace(',', '').strip()
        if clean_str.lower() == 'none' or clean_str == '': return 0.0
        return float(clean_str)
    except ValueError: return 0.0

def render_system_stats():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    st.sidebar.caption(f"SYSTEM HEALTH: CPU {cpu}% | RAM {ram}%")
    st.sidebar.progress(cpu / 100)

# --- MODAL: UPLOAD DIALOG ---
@st.dialog("Add New Document")
def render_upload_modal():
    st.write("Upload PDF, JPG, or CSV files to your workspace.")
    uploaded_files = st.file_uploader("Drag & drop files here", accept_multiple_files=True, label_visibility="collapsed")
    
    if uploaded_files:
        if st.button("🚀 Process Files", use_container_width=True):
            progress_bar = st.progress(0)
            status = st.empty()
            os.makedirs("output", exist_ok=True)
            db = DatabaseEngine()
            
            for i, f in enumerate(uploaded_files):
                status.text(f"Processing {f.name}...")
                bytes_data = f.getvalue()
                file_hash = get_file_hash(bytes_data)
                save_path = os.path.join("output", f.name)
                with open(save_path, "wb") as out: out.write(bytes_data)
                
                if db.check_file_hash(file_hash):
                    status.info(f"Skipped {f.name} (Cached)")
                    continue

                try:
                    # HYBRID PIPELINE (C++ / Pandas)
                    raw_text = ""
                    cpp_data = {}
                    if f.name.lower().endswith('.csv'):
                        df = pd.read_csv(save_path)
                        raw_text = df.head(1000).to_markdown(index=False)
                        cpp_data = {"method": "CSV"}
                    else:
                        result = subprocess.run(["./build/docproc", save_path], capture_output=True, text=True)
                        if result.returncode == 0:
                            cpp_data = json.loads(result.stdout)
                            raw_text = cpp_data.get('content', '')
                        else:
                            st.error(f"Engine failed on {f.name}")
                            continue
                    
                    # AI Analysis
                    brain = DocumentBrain()
                    ai_data = brain.analyze_document(raw_text)
                    db.save_document(f.name, save_path, raw_text, ai_data, cpp_data, file_hash)
                    
                except Exception as e:
                    st.error(f"Error: {e}")
                
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            status.success("Upload Complete!")
            time.sleep(1)
            st.rerun()
# ========================================================
# 🛑 END OF MODAL FUNCTION. DO NOT INDENT CODE BELOW THIS.
# ========================================================

# ==========================================
# SIDEBAR NAVIGATION
# ==========================================
with st.sidebar:
    st.image("https://placehold.co/200x50/111827/ffffff?text=XENTRO+AI", width=180)
    st.markdown("### Workspace")

    # THE MENU (Replaces st.radio) - larger text/icons
    app_mode = option_menu(
        menu_title="Workspace",
        options=["Documents", "Chats", "Global Intel", "Risk Audit", "Privacy Vault"],
        icons=["file-earmark-text", "chat-dots", "globe", "shield-exclamation", "lock"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "5px!important", "background-color": "transparent"},
            # --- INCREASED SIZES ---
            "icon": {"color": "#200e56", "font-size": "20px"},
            "nav-link": {
                "font-size": "18px",
                "text-align": "left",
                "margin": "8px",
                "color": "#99b4e4",
                "--hover-color": "#262038"
            },
            "nav-link-selected": {"background-color": "#262038", "border-left": "4px solid #8b5cf6"},
        }
    )

    st.markdown("---")
    render_system_stats()

# ==========================================
# PAGE 1: DOCUMENTS (Manager + MathGuard)
# ==========================================
if app_mode == "Documents":
    c1, c2 = st.columns([6, 1])
    c1.title("Documents")
    if c2.button("➕ Add", use_container_width=True): render_upload_modal()

    db = DatabaseEngine()
    try:
        docs = db.get_recent_documents(limit=50)
        if not docs:
            UIEngine.render_empty_state("No documents yet", "Upload a file to start analyzing.")
        else:
            filter_text = st.text_input("🔍 Search files...", "")
            
            for doc in docs:
                if filter_text.lower() in doc.filename.lower():
                    with st.expander(f"📄 {doc.filename}  |  {doc.metadata_json.get('vendor', 'Unknown')}  |  {doc.processed_at.strftime('%Y-%m-%d')}"):
                        
                        # MATHGUARD INTEGRATION
                        st.markdown("**🛡️ MathGuard Audit**")
                        # Unique key for each button is critical in loops
                        if st.button(f"Verify Math", key=f"math_{doc.id}"):
                            brain = DocumentBrain()
                            audit = brain.verify_math(doc.text_content)
                            
                            m1, m2, m3 = st.columns(3)
                            m1.metric("Subtotal", f"${audit.get('found_subtotal', 0)}")
                            m2.metric("Tax", f"${audit.get('found_tax', 0)}")
                            m3.metric("Calc. Total", f"${audit.get('calculated_total', 0)}")
                            
                            if audit.get('is_math_correct'):
                                st.success("✅ Integrity Verified")
                            else:
                                st.error("⚠️ Discrepancy Detected")
                                st.caption(audit.get('explanation'))

                        st.divider()
                        st.markdown("**📝 AI Summary**")
                        st.info(doc.ai_summary)
                        st.json(doc.metadata_json)

    except Exception as e:
        st.error(f"Database Error: {e}")

# ==========================================
# PAGE 2: CHATS (RAG Interface)
# ==========================================
elif app_mode == "Chats":
    st.title("Chats")
    db = DatabaseEngine()
    docs = db.get_recent_documents(20)
    doc_names = [d.filename for d in docs] if docs else []
    
    if not doc_names:
        UIEngine.render_empty_state("No chats available", "Upload documents first.")
    else:
        c_list, c_chat = st.columns([1, 2])
        with c_list:
            st.caption("CONTEXT")
            selected_doc = st.selectbox("Active Document:", ["All Documents"] + doc_names)
            if st.button("🗑️ Clear"): st.session_state['chat_history'] = []; st.rerun()

        with c_chat:
            chat_box = st.container(height=500)
            with chat_box:
                for msg in st.session_state['chat_history']:
                    align = "right" if msg['role'] == 'user' else "left"
                    bg = "#f3f4f6" if msg['role'] == 'user' else "#ffffff"
                    border = "1px solid #10b981" if msg['role'] == 'ai' else "none"
                    st.markdown(f"<div style='text-align:{align}; background:{bg}; padding:10px; border-radius:10px; margin:5px; border:{border}; display:inline-block;'>{msg['content']}</div>", unsafe_allow_html=True)

            q = st.chat_input("Ask a question...")
            if q:
                st.session_state['chat_history'].append({'role': 'user', 'content': q})
                brain = DocumentBrain()
                if selected_doc == "All Documents":
                    results = db.query_similar_docs(q, n_results=5)
                else:
                    results = db.query_similar_docs(q, filename_filter=selected_doc)
                
                context = "\n".join(results['documents'][0]) if results['documents'] else ""
                ans = brain.chat_with_documents(context, q)
                st.session_state['chat_history'].append({'role': 'ai', 'content': ans})
                st.rerun()

# ==========================================
# PAGE 3: GLOBAL INTEL (Cross-Doc Search)
# ==========================================
elif app_mode == "Global Intel":
    st.title("Global Intelligence")
    st.markdown("Ask questions across **your entire knowledge base**.")
    
    user_q = st.text_input("Executive Query:", placeholder="e.g. 'How much did we pay Microsoft last year?'")
    if user_q:
        db = DatabaseEngine()
        results = db.query_global_context(user_q, n_results=10)
        
        if results['documents']:
            context = "\n".join(results['documents'][0])
            brain = DocumentBrain()
            with st.spinner("🧠 Analyzing Enterprise Data..."):
                answer = brain.chat_with_documents(context, user_q)
            st.info(answer)
            with st.expander("Source Data"): st.text(context)
        else:
            st.warning("No data found.")

# ==========================================
# PAGE 4: RISK AUDIT (Anomaly Detection)
# ==========================================
elif app_mode == "Risk Audit":
    st.title("Risk & Fraud Auditor")
    db = DatabaseEngine()
    docs = db.get_recent_documents(50)
    options = {d.filename: d for d in docs}
    
    if not options:
        UIEngine.render_empty_state("No data to audit", "Upload documents first.")
    else:
        selected_file = st.selectbox("Select Invoice to Audit:", list(options.keys()))
        if st.button("⚡ Run Forensic Check"):
            target = options[selected_file]
            vendor = target.metadata_json.get('vendor', '')
            
            with st.spinner("🔍 Checking Historical Patterns..."):
                history = db.get_vendor_history(vendor, exclude_filename=target.filename)
                brain = DocumentBrain()
                audit = brain.audit_document(target.text_content, history)
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Risk Score", f"{audit.get('risk_score')}/100")
                c2.metric("Level", audit.get('risk_level'))
                c3.metric("Action", audit.get('recommendation'))
                
                st.error(f"Flags: {audit.get('flags')}")
                with st.expander("Historical Baseline"): st.json(history)

# ==========================================
# PAGE 5: PRIVACY VAULT (Redaction)
# ==========================================
elif app_mode == "Privacy Vault":
    st.title("Privacy Vault (GDPR)")
    db = DatabaseEngine()
    docs = db.get_recent_documents(50)
    options = {d.filename: d for d in docs}
    
    if not options:
        UIEngine.render_empty_state("Vault Empty", "Upload documents first.")
    else:
        selected_file = st.selectbox("Select Document to Redact:", list(options.keys()))
        if st.button("🔒 Generate Public Version"):
            target = options[selected_file]
            with st.spinner("🕵️ Scrubbing PII..."):
                brain = DocumentBrain()
                redacted = brain.redact_sensitive_data(target.metadata_json)
                
                c1, c2 = st.columns(2)
                with c1: 
                    st.markdown("**Original**")
                    st.json(target.metadata_json)
                with c2: 
                    st.markdown("**Sanitized**")
                    st.json(redacted)
                
                st.download_button("Download JSON", data=json.dumps(redacted), file_name="safe.json")