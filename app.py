import streamlit as st
import pandas as pd
import time
import re
from datetime import datetime
import yfinance as yf
from supabase import create_client, Client
import extra_streamlit_components as stx

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
    .free-box {
        background-color: #111827;
        padding: 18px;
        border-radius: 10px;
        border: 1px solid #e11d48;
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

# --- BROWSER COOKIE MANAGER ---
cookie_manager = stx.CookieManager()
time.sleep(0.1)

c_logged_in = cookie_manager.get(cookie="xau_logged_in")
c_role = cookie_manager.get(cookie="xau_role")
c_email = cookie_manager.get(cookie="xau_email")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = True if c_logged_in == "true" else False
if "role" not in st.session_state:
    st.session_state.role = c_role if c_role else None
if "user_email" not in st.session_state:
    st.session_state.user_email = c_email if c_email else None

def clean_html_tags(text):
    return re.sub(r'<[^>]*>', '', str(text))

# --- AUTHENTICATION SCREEN ---
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center; margin-top: 40px;'>🔒 XAUUSD VIP AI Terminal</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Algorithmic Multi-Agent Intelligence Network</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        tab1, tab2, tab3 = st.tabs(["🔑 Sign In", "💳 Activate VIP", "🎁 Free Trial Account"])
        
        with tab1:
            email_input = st.text_input("Registered Email ID", key="login_email")
            whatsapp_input = st.text_input("WhatsApp Security Key / Password", type="password", key="login_pass")
            
            if st.button("Access Hub", use_container_width=True):
                if email_input == "manishadmin" and whatsapp_input == "goldmaster77":
                    st.session_state.logged_in = True
                    st.session_state.role = "ADMIN"
                    st.session_state.user_email = "Manissh S Jariwala (Admin)"
                    cookie_manager.set("xau_logged_in", "true", max_age=604800)
                    cookie_manager.set("xau_role", "ADMIN", max_age=604800)
                    cookie_manager.set("xau_email", "Manissh S Jariwala (Admin)", max_age=604800)
                    st.rerun()
                elif "@" in email_input and whatsapp_input == "free123":
                    st.session_state.logged_in = True
                    st.session_state.role = "FREE"
                    st.session_state.user_email = email_input
                    st.rerun()
                else:
                    try:
                        res = supabase.table("users").select("*").eq("email", email_input).eq("whatsapp", whatsapp_input).execute()
                        if len(res.data) > 0:
                            st.session_state.logged_in = True
                            st.session_state.role = "USER"
                            st.session_state.user_email = res.data[0]["email"]
                            cookie_manager.set("xau_logged_in", "true", max_age=604800)
                            cookie_manager.set("xau_role", "USER", max_age=604800)
                            cookie_manager.set("xau_email", res.data[0]["email"], max_age=604800)
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
                <span style='font-size:0.85rem; color:#9ca3af;'>⚠️ Note: Submit TXID below for instant validation.</span>
            </div>
            """, unsafe_allow_html=True)
            reg_email = st.text_input("Enter Email", key="reg_email")
            reg_whatsapp = st.text_input("WhatsApp Number", key="reg_wa")
            reg_txid = st.text_input("Transaction ID (TXID)", key="reg_tx")
            if st.button("Submit VIP Activation Request", use_container_width=True):
                if reg_email and reg_whatsapp and reg_txid:
                    try:
                        supabase.table("users").insert({"email": reg_email, "whatsapp": reg_whatsapp, "txid": reg_txid, "status": "Pending"}).execute()
                        st.success("Payment Logged! Admin will verify and activate your hub within 15 minutes.")
                    except:
                        st.error("Sync error.")
        
        with tab3:
            st.markdown("""
            <div class='free-box'>
                <b>🎁 Instantly Create a Free Trial Account</b><br>
                Free tier accounts can explore the executive dashboard workspace layout and track live gold pricing models instantly.
            </div>
            """, unsafe_allow_html=True)
            free_email = st.text_input("Enter Your Email Address", key="free_email_reg")
            if st.button("Create Free Account & Login", use_container_width=True):
                if free_email and "@" in free_email:
                    st.session_state.logged_in = True
                    st.session_state.role = "FREE"
                    st.session_state.user_email = free_email
                    st.success("Welcome aboard! Loading dashboard framework...")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Please enter a valid email address.")

# --- LIVE WORKSPACE ---
else:
    st.sidebar.markdown("### 🛡️ Secure Session Active")
    st.sidebar.markdown(f"**User:** `{st.session_state.user_email}`")
    st.sidebar.markdown(f"**Access Tier:** `{st.session_state.role}`")
    
    workspace_mode = st.sidebar.radio("Navigate View", ["📢 Live Trading Hub", "🤖 AI Agent Activity Log"])
    
    if st.sidebar.button("Exit Dashboard 🚪", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.user_email = None
        cookie_manager.delete("xau_logged_in")
        cookie_manager.delete("xau_role")
        cookie_manager.delete("xau_email")
        st.rerun()

    # PRICE ENGINE SYNC
    try:
        gold_ticker = yf.Ticker("GC=F")
        raw_price = gold_ticker.history(period="1d")["Close"].iloc[-1]
        calibrated_spot = raw_price - 19.20
        if calibrated_spot < 3500:  
            calibrated_spot = 4024.15
        live_price_str = f"${calibrated_spot:.2f}"
    except:
        live_price_str = "$4024.15"

    # Fetch Google Sheet Data Pipeline
    try:
        df = pd.read_csv(SHEET_TSV_URL, sep="\t").dropna(how='all', axis=1).fillna("")
        items = []
        for c, v in df.iloc[-1].items():
            if "Unnamed" not in str(c) and str(v).strip() and str(v).lower() != "none":
                items.append(f"<b>{c}:</b> {v}")
        latest_signal = " | ".join(items) if items else f"🚀 VIP Trading Signal Active at {live_price_str}"
        sheet_active = True
    except:
        latest_signal = f"🚀 XAUUSD SCALPER ALERT | Active CMP: {live_price_str} | Strategy Configured"
        sheet_active = False

    # WELCOME MESSAGE RULES PER TIER
    if st.session_state.role == "FREE":
        st.toast(f"Welcome {st.session_state.user_email}! You are exploring on a Free Trial Account.")
        st.markdown(f"""
        <div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left:6px solid #e11d48; margin-bottom:15px;'>
            <h4 style='margin:0; color:#e11d48;'>👋 Welcome to XAUUSD AI Trial Hub, {st.session_state.user_email}!</h4>
            <p style='margin:5px 0 0 0; font-size:0.95rem; color:#cbd5e1;'>You are currently viewing limited historical analytical structures. Upgrade to the VIP Tier to unlock live execution broadcast streams and alpha pipelines instantly.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left:6px solid #10b981; margin-bottom:15px;'>
            <h4 style='margin:0; color:#10b981;'>👑
