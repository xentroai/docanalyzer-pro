import streamlit as st
import subprocess
import os
import json
import pandas as pd
import altair as alt
import hashlib
import psutil
import re
import concurrent.futures
from datetime import datetime
from llm_engine import DocumentBrain
from db_engine import DatabaseEngine
from ui_engine import UIEngine

# 1. Page Configuration
st.set_page_config(page_title="Xentro DocAnalyzer Pro", page_icon="🧠", layout="wide")

# 2. Session State
if 'processed_data' not in st.session_state: st.session_state['processed_data'] = None
if 'chat_history' not in st.session_state: st.session_state['chat_history'] = []
if 'active_filename' not in st.session_state: st.session_state['active_filename'] = None
if 'batch_results' not in st.session_state: st.session_state['batch_results'] = []
if 'theme_mode' not in st.session_state: st.session_state['theme_mode'] = 'dark'

# --- HELPERS ---
def safe_float(val):
    if val is None: return 0.0
    try:
        clean_str = str(val).replace('$', '').replace(',', '').strip()
        if clean_str.lower() == 'none' or clean_str == '': return 0.0
        return float(clean_str)
    except ValueError: return 0.0

def smart_rename_file(original_path, ai_data):
    try:
        vendor = ai_data.get('vendor', 'Unknown').replace(" ", "")
        vendor = re.sub(r'[^A-Za-z0-9]', '', vendor)[:15] 
        doc_type = ai_data.get('type', 'DOC').upper()
        date_str = ai_data.get('date', datetime.now().strftime('%Y-%m-%d'))
        if len(date_str) < 8: date_str = datetime.now().strftime('%Y-%m-%d')

        dir_name = os.path.dirname(original_path)
        ext = os.path.splitext(original_path)[1]
        new_filename = f"{date_str}_{vendor}_{doc_type}{ext}"
        new_path = os.path.join(dir_name, new_filename)
        os.rename(original_path, new_path)
        return new_filename, new_path
    except Exception as e:
        return None, str(e)

def render_system_stats():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    c1, c2 = st.columns(2)
    c1.metric("CPU", f"{cpu}%")
    c2.metric("RAM", f"{ram}%")
    st.progress(cpu / 100)

def get_file_hash(file_bytes):
    return hashlib.md5(file_bytes).hexdigest()

def inject_custom_css(theme):
    if theme == 'dark':
        bg_color, card_bg, text_color = "#0e1117", "#262730", "white"
        accent, secondary = "#00f2fe", "#4facfe"
        chat_user, chat_ai, border_color = "#2b313e", "#1c1f26", "#464b5c"
    else:
        bg_color, card_bg, text_color = "#f0f2f6", "#ffffff", "#31333F"
        accent, secondary = "#2563eb", "#3b82f6"
        chat_user, chat_ai, border_color = "#e5e7eb", "#ffffff", "#e5e7eb"

    st.markdown(f"""
    <style>
        .stApp {{ background-color: {bg_color}; color: {text_color}; }}
        div[data-testid="stMetric"] {{
            background-color: {card_bg}; border: 1px solid {border_color};
            padding: 15px; border-radius: 10px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }}
        div[data-testid="stMetricLabel"] {{ color: {text_color} !important; opacity: 0.7; }}
        div[data-testid="stMetricValue"] {{ color: {text_color} !important; }}
        .chat-user {{
            background-color: {chat_user}; color: {text_color}; padding: 15px;
            border-radius: 15px 15px 0px 15px; margin: 10px 0; text-align: right;
            border-right: 3px solid {secondary};
        }}
        .chat-ai {{
            background-color: {chat_ai}; color: {text_color}; padding: 15px;
            border-radius: 15px 15px 15px 0px; margin: 10px 0; border-left: 3px solid {accent};
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }}
        .hud-header {{
            font-family: 'Courier New', monospace; color: {accent};
            border-bottom: 1px solid {accent}; padding-bottom: 5px; margin-bottom: 15px;
            letter-spacing: 2px; text-transform: uppercase; font-weight: bold; font-size: 0.9em;
        }}
        div.stButton > button {{
            background: linear-gradient(90deg, {accent} 0%, {secondary} 100%);
            color: white; border: none; font-weight: bold; transition: transform 0.2s;
        }}
        div.stButton > button:hover {{ transform: scale(1.02); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }}
    </style>
    """, unsafe_allow_html=True)

# --- NEW: PARALLEL WORKER FUNCTION ---
def process_single_file(file_info):
    """
    This runs inside a thread. It handles C++ and AI for ONE file.
    """
    save_path = file_info['path']
    filename = file_info['name']
    file_hash = file_info['hash']
    
    try:
        # CSV Bypass
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(save_path)
            raw_text = df.head(1000).to_markdown(index=False)
            cpp_data = {"method": "PYTHON_PANDAS_CSV", "debug": None}
        else:
            # C++ Engine
            cpp_binary = "./build/docproc"
            result = subprocess.run([cpp_binary, save_path], capture_output=True, text=True)
            
            if result.returncode != 0:
                return {"error": f"C++ Failed for {filename}"}
                
            cpp_data = json.loads(result.stdout)
            raw_text = cpp_data.get('content', '')
        
        # AI Analysis
        brain = DocumentBrain()
        ai_analysis = brain.analyze_document(raw_text)
        
        return {
            "filename": filename,
            "filepath": save_path,
            "data": ai_analysis,
            "raw_text": raw_text,
            "cpp": cpp_data,
            "hash": file_hash,
            "success": True
        }
        
    except Exception as e:
        return {"error": f"Error in {filename}: {str(e)}", "success": False}

# --- LOGIC: CHAT ---
def process_chat_query(question):
    if not st.session_state.get('active_filename'):
        UIEngine.render_error_toast("System Offline", "No active document context found.")
        return

    with st.spinner("⚡ Neural Engine Processing..."):
        try:
            db = DatabaseEngine()
            results = db.query_similar_docs(question, filename_filter=st.session_state['active_filename'])
            context = "\n\n".join(results['documents'][0]) if results['documents'] else ""
            
            brain = DocumentBrain()
            if st.session_state.get('current_raw_text'):
                full_context = f"--- RAW TEXT ---\n{st.session_state['current_raw_text']}"
            else:
                full_context = context

            answer = brain.chat_with_documents(full_context, question)
            
            st.session_state['chat_history'].append({'role': 'user', 'content': question})
            st.session_state['chat_history'].append({'role': 'ai', 'content': answer})
            return True
        except Exception as e:
            UIEngine.render_error_toast("Chat Error", str(e))
            return False

# 3. Sidebar
with st.sidebar:
    st.image("https://placehold.co/200x50?text=XENTRO+AI", width=200)
    st.markdown("---")
    
    mode = st.toggle("🌙 Dark Mode", value=True)
    st.session_state['theme_mode'] = 'dark' if mode else 'light'
    inject_custom_css(st.session_state['theme_mode'])
    
    st.markdown("---")
    st.caption("MODE SELECTION")
    app_mode = st.radio("Select Module", ["🚀 Processor", "🌎 Global Intelligence", "🔍 Anomaly Auditor", "🛡️ Privacy Vault"])
    
    st.markdown("---")
    st.markdown("**🖥️ System Health**")
    render_system_stats()

# ==========================================
# MAIN ROUTER
# ==========================================

if app_mode == "🚀 Processor":
    title_color = "white" if st.session_state['theme_mode'] == 'dark' else "#31333F"
    st.markdown(f"<h1 style='text-align: center; color: {title_color};'>DOCANALYZER <span style='color: #00f2fe'>PRO</span></h1>", unsafe_allow_html=True)

    uploaded_files = st.file_uploader(" ", type=["pdf", "jpg", "png", "csv"], accept_multiple_files=True, label_visibility="collapsed")

    if uploaded_files:
        if st.button(f"⚡ PROCESS {len(uploaded_files)} FILES (PARALLEL)", use_container_width=True):
            st.session_state['batch_results'] = []
            st.session_state['chat_history'] = []
            
            # 1. PREPARE FILES (Main Thread)
            file_queue = []
            os.makedirs("output", exist_ok=True)
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            status_text.markdown("`[INIT] Staging files for parallel execution...`")
            
            for f in uploaded_files:
                file_bytes = f.getvalue()
                save_path = os.path.join("output", f.name)
                with open(save_path, "wb") as out:
                    out.write(file_bytes)
                
                file_queue.append({
                    "name": f.name,
                    "path": save_path,
                    "hash": get_file_hash(file_bytes)
                })

            # 2. PARALLEL EXECUTION
            completed_count = 0
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_file = {executor.submit(process_single_file, f): f for f in file_queue}
                
                for future in concurrent.futures.as_completed(future_to_file):
                    result = future.result()
                    if result.get("success"):
                        st.session_state['batch_results'].append(result)
                        try:
                            db = DatabaseEngine()
                            db.save_document(
                                result['filename'], 
                                result['filepath'], 
                                result['raw_text'], 
                                result['data'], 
                                result['cpp'], 
                                result['hash']
                            )
                        except Exception as e:
                            print(f"DB Save Warning: {e}")
                    elif "error" in result:
                        st.error(result['error'])
                    
                    completed_count += 1
                    progress_bar.progress(completed_count / len(uploaded_files))
                    status_text.markdown(f"`[PROCESSING] Completed {completed_count}/{len(uploaded_files)}...`")

            status_text.success(f"✅ Parallel Processing Complete! ({len(st.session_state['batch_results'])}/{len(uploaded_files)} success)")
            
            if st.session_state['batch_results']:
                st.session_state['active_filename'] = st.session_state['batch_results'][-1]['filename']
                st.session_state['current_raw_text'] = st.session_state['batch_results'][-1]['raw_text']
            else:
                st.warning("No documents were successfully processed.")

    # DASHBOARD VIEW
    if st.session_state['batch_results']:
        results = st.session_state['batch_results']
        total_docs = len(results)
        total_value = sum([safe_float(r['data'].get('total_amount')) for r in results])
        
        st.markdown("---")
        col_dash, col_chat = st.columns([1.6, 1])
        
        with col_dash:
            st.markdown("<div class='hud-header'>Batch Telemetry</div>", unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            m1.metric("Files", str(total_docs))
            m2.metric("Total Value", f"${total_value:,.2f}")
            m3.metric("Engine", "Parallel C++")

            if st.button("📂 Auto-Rename Files"):
                count = 0
                for r in results:
                    old_path = r.get('filepath')
                    if old_path and os.path.exists(old_path):
                        _, new_path = smart_rename_file(old_path, r['data'])
                        if new_path: count += 1
                st.success(f"Renamed {count} files.")
                st.rerun()

            t1, t2, t3 = st.tabs(["📝 Overview", "📊 Data", "📈 Trends"])
            with t1:
                last = results[-1]
                st.info(f"**Latest ({last['filename']}):** " + last['data'].get('summary', 'No summary.'))
                
                # MathGuard
                with st.status("🛡️ Running MathGuard Audit...", expanded=False) as status:
                    brain = DocumentBrain()
                    # Safety check
                    if not last['raw_text'] or len(last['raw_text']) < 10:
                        status.update(label="⚠️ MathGuard Skipped: No text extracted", state="error")
                    else:
                        audit = brain.verify_math(last['raw_text'])
                        sub = safe_float(audit.get('found_subtotal'))
                        disc = safe_float(audit.get('found_discount'))
                        ship = safe_float(audit.get('found_shipping'))
                        tax = safe_float(audit.get('found_tax'))
                        calc = safe_float(audit.get('calculated_total'))
                        found = safe_float(audit.get('found_total'))

                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Subtotal", f"${sub:,.2f}")
                        c2.metric("Discount", f"-${disc:,.2f}")
                        c3.metric("Ship/Tax", f"+${(ship + tax):,.2f}")
                        c4.metric("Calculated", f"${calc:,.2f}")
                        
                        if audit.get('is_math_correct'):
                            status.update(label="✅ Integrity Verified", state="complete", expanded=True)
                            st.caption(f"✨ {audit.get('explanation')}")
                        else:
                            status.update(label="⚠️ Discrepancy Detected", state="error", expanded=True)
                            st.error(f"❌ Document says ${found:,.2f}, but math says ${calc:,.2f}")
                            st.caption(f"Reason: {audit.get('explanation')}")
                        
                        with st.expander("🔍 View Raw Logic Input"):
                            st.code(last['raw_text'][:1000])

            with t2:
                table_data = []
                for r in results:
                    conf = r['data'].get('confidence_score', 0)
                    icon = "🟢" if conf > 80 else ("🟡" if conf > 50 else "🔴")
                    table_data.append({
                        "Risk": icon,
                        "File": r['filename'],
                        "Vendor": r['data'].get('vendor'),
                        "Amount": safe_float(r['data'].get('total_amount'))
                    })
                st.dataframe(pd.DataFrame(table_data), use_container_width=True)
            with t3:
                if total_value > 0:
                    chart_data = pd.DataFrame(table_data)
                    pie = alt.Chart(chart_data).mark_arc(innerRadius=50).encode(
                        theta=alt.Theta("Amount", stack=True), color="Vendor", tooltip=["Vendor", "Amount"]
                    )
                    st.altair_chart(pie, use_container_width=True)

        with col_chat:
            st.markdown("<div class='hud-header'>Neural Uplink</div>", unsafe_allow_html=True)
            chat_cont = st.container(height=500)
            with chat_cont:
                for msg in st.session_state['chat_history']:
                    role = "chat-user" if msg['role']=='user' else "chat-ai"
                    st.markdown(f"<div class='{role}'>{msg['content']}</div>", unsafe_allow_html=True)
            q = st.chat_input("Ask about the batch...")
            if q:
                if process_chat_query(q): st.rerun()
    else:
        UIEngine.render_empty_state()

elif app_mode == "🌎 Global Intelligence":
    def render_global_intelligence():
        st.markdown(f"<h2 style='color: #00f2fe;'>🌎 GLOBAL INTELLIGENCE</h2>", unsafe_allow_html=True)
        st.markdown("Ask questions across **all** uploaded contracts and invoices.")
        user_q = st.text_input("Executive Query:", placeholder="e.g. 'How much did we pay Microsoft in total last year?'")
        if user_q:
            db = DatabaseEngine()
            results = db.query_global_context(user_q, n_results=10)
            if results['documents']:
                context = "\n".join(results['documents'][0])
                brain = DocumentBrain()
                with st.spinner("🧠 Cross-referencing Knowledge Base..."):
                    answer = brain.chat_with_documents(context, user_q)
                st.markdown("### 🤖 Executive Summary")
                st.info(answer)
                with st.expander("View Source Documents"):
                    st.text(context)
            else:
                st.warning("No relevant data found.")
    render_global_intelligence()

elif app_mode == "🔍 Anomaly Auditor":
    def render_anomaly_auditor():
        st.markdown(f"<h2 style='color: #00f2fe;'>🔍 ANOMALY AUDITOR</h2>", unsafe_allow_html=True)
        
        # Database Inspector
        with st.expander("🕵️ View All Known Vendors (Debug Database)"):
            try:
                db = DatabaseEngine()
                vendor_counts = db.get_all_vendors()
                if vendor_counts:
                    st.dataframe(pd.DataFrame(list(vendor_counts.items()), columns=["Vendor Name", "Invoice Count"]), use_container_width=True)
                else:
                    st.info("Database is empty.")
            except Exception as e:
                st.error(f"Could not inspect DB: {e}")

        if not st.session_state['batch_results']:
            st.info("Upload documents in 'Processor' first.")
            return
            
        options = {r['filename']: r for r in st.session_state['batch_results']}
        selected_file = st.selectbox("Select Invoice to Audit:", list(options.keys()))
        
        if st.button("⚡ RUN FORENSIC CHECK"):
            target_doc = options[selected_file]
            vendor = target_doc['data'].get('vendor', '')
            current_filename = target_doc['filename']
            
            with st.spinner(f"🔍 Searching historical records for '{vendor}'..."):
                db = DatabaseEngine()
                history = db.get_vendor_history(vendor, exclude_filename=current_filename)
                brain = DocumentBrain()
                audit_result = brain.audit_document(target_doc['raw_text'], history)
                
                r_col1, r_col2, r_col3 = st.columns(3)
                score = audit_result.get('risk_score', 0)
                r_col1.metric("Risk Score", f"{score}/100")
                r_col2.metric("Risk Level", audit_result.get('risk_level', 'UNKNOWN'))
                r_col3.metric("AI Verdict", audit_result.get('recommendation', 'Review'))
                
                st.markdown("---")
                st.markdown("### 🚩 Detected Flags")
                for flag in audit_result.get('flags', []):
                    st.error(f"• {flag}")
                
                with st.expander("View Historical Context"):
                    st.write(f"Found {len(history)} past invoices for {vendor}:")
                    st.json(history)
    render_anomaly_auditor()

elif app_mode == "🛡️ Privacy Vault":
    def render_privacy_vault():
        st.markdown(f"<h2 style='color: #00f2fe;'>🛡️ PRIVACY VAULT</h2>", unsafe_allow_html=True)
        if not st.session_state['batch_results']:
            st.info("Upload documents in 'Processor' first.")
            return
        
        st.markdown("### 🔒 GDPR/PII Auto-Redaction")
        options = {r['filename']: r for r in st.session_state['batch_results']}
        selected_file = st.selectbox("Select Document to Sanitize:", list(options.keys()))
        
        if st.button("⚡ GENERATE PUBLIC VERSION"):
            target_doc = options[selected_file]
            original_data = target_doc['data']
            
            with st.spinner("🕵️ Scrubbing sensitive data..."):
                brain = DocumentBrain()
                redacted_data = brain.redact_sensitive_data(original_data)
                
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("🔴 Original (Private)")
                    st.json(original_data)
                with c2:
                    st.subheader("🟢 Sanitized (Public)")
                    st.json(redacted_data)
                
                st.markdown("---")
                st.download_button(
                    "📥 Download Safe JSON", 
                    data=json.dumps(redacted_data, indent=2), 
                    file_name=f"SAFE_{selected_file}.json"
                )
    render_privacy_vault()