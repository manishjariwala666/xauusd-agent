import streamlit as st
import pandas as pd
import time
import re
from datetime import datetime
import yfinance as yf
from supabase import create_client, Client

# --- SETTINGS & CONFIG ---
st.set_page_config(page_title="XAUUSD VIP AI Terminal", page_icon="💰", layout="wide")

st.markdown("""
<style>
    .reportview-container { background: #0e1117; }
    .chat-message-admin {
        background-color: #1f2937;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
        border-left: 6px solid #f59e0b;
        color: #f3f4f6;
    }
    .agent-card {
        background-color: #111827;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #374151;
        margin-bottom: 10px;
    }
    .status-card {
        background-color: #111827;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #374151;
        margin-bottom: 15px;
    }
    .wallet-box {
        background-color: #1e3a8a;
        padding: 18px;
        border-radius: 10px;
        border: 1px solid #3b82f6;
        color: white;
        margin-bottom: 20px;
    }
    .log-box {
        background-color: #070a12;
        padding: 12px;
        font-family: monospace;
        color: #38bdf8;
        border-radius: 6px;
        border: 1px solid #1e293b;
        margin-bottom: 8px;
    }
    th { background-color: #1f2937 !important; color: #f59e0b !important; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION ---
SUPABASE_URL = "https://tdgyhqlxoyfkkrhzljwo.supabase.co"
SUPABASE_KEY = "sb_secret_R4xiW5szyOxyrFPRRotsyw_RTiYFWWf"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- GOOGLE SHEET TSV LINK ---
SHEET_TSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRc2bZvbbN8-_7HXt-Cu0_UPmUpLEcpOcGQimQj8j1Q39i4Hr4E8tjhMCX5krQSAsX4kXwYpzwn5BjC/pub?output=tsv"

# --- PERSISTENT SESSION SYSTEM (REFRESH-PROOF) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# Helper function to remove raw HTML tags for clean editing
def clean_html_tags(text):
    return re.sub(r'<[^>]*>', '', str(text))

# --- AUTHENTICATION & REGISTRATION ---
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center; margin-top: 40px;'>🔒 XAUUSD VIP AI Terminal</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Algorithmic Multi-Agent Intelligence Network</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.3, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["🔑 Sign In Terminal", "💳 Activate VIP Subscription"])
        
        with tab1:
            email_input = st.text_input("Registered Email ID", key="login_email")
            whatsapp_input = st.text_input("WhatsApp Security Key (Password)", type="password", key="login_pass")
            
            if st.button("Access Hub", use_container_width=True):
                if email_input == "manishadmin" and whatsapp_input == "goldmaster77":
                    st.session_state.logged_in = True
                    st.session_state.role = "ADMIN"
                    st.session_state.user_email = "Manissh S Jariwala (Admin)"
                    st.rerun()
                else:
                    try:
                        res = supabase.table("users").select("*").eq("email", email_input).eq("whatsapp", whatsapp_input).execute()
                        if len(res.data) > 0:
                            st.session_state.logged_in = True
                            st.session_state.role = "USER"
                            st.session_state.user_email = res.data[0]["email"]
                            st.rerun()
                        else:
                            st.error("Invalid VIP Access Credentials.")
                    except:
                        st.error("Authentication Network Error.")
                        
        with tab2:
            st.markdown(f"""
            <div class='wallet-box'>
                <b>✨ VIP Deposit Wallet Address (USDT TRC20):</b><br>
                <code style='color:#facc15; font-size:1.05rem; word-break: break-all;'>TWeNUrS2617xUssfkT9SHjU6XxZAYADaa8</code><br><br>
                <b>UPI ID (Indian Users Bank Transfer):</b><br>
                <code style='color:#facc15; font-size:1.05rem;'>manissh.jariwala@okaxis</code><br><br>
                <span style='font-size:0.85rem; color:#9ca3af;'>⚠️ Note: Send TRON-based tokens only. Submit TXID below for instant verification.</span>
            </div>
            """, unsafe_allow_html=True)
            
            reg_email = st.text_input("Enter Email", key="reg_email")
            reg_whatsapp = st.text_input("WhatsApp Number", key="reg_wa")
            reg_txid = st.text_input("Payment Reference / Transaction ID (TXID)", key="reg_tx")
            
            if st.button("Submit VIP Activation Request", use_container_width=True):
                if reg_email and reg_whatsapp and reg_txid:
                    try:
                        supabase.table("users").insert({"email": reg_email, "whatsapp": reg_whatsapp, "txid": reg_txid, "status": "Pending"}).execute()
                        st.success("Payment Logged Successfully! Admin will verify and activate your hub within 15 minutes.")
                    except:
                        st.error("Registration synchronization error.")
                else:
                    st.warning("Please fill out all activation fields.")

# --- LIVE WORKSPACE ---
else:
    # Sidebar Navigation System
    st.sidebar.markdown(f"
