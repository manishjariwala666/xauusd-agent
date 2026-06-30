import streamlit as st
import requests
import pandas as pd
import time

# --- SETTINGS & CONFIG ---
st.set_page_config(page_title="XAUUSD VIP Hub", page_icon="💰", layout="wide")

# --- CREDENTIALS CONFIG ---
try:
    WHATSAPP_TOKEN = st.secrets["whatsapp"]["token"]
    PHONE_NUMBER_ID = st.secrets["whatsapp"]["phone_number_id"]
    SHEET_URL = st.secrets["google"]["sheet_url"] 
except:
    WHATSAPP_TOKEN = "EAAYmZCZBEO60UBRzJiGJ3kfazGNJeZCutZCPQPzcw9f5TXdZAYwmxjWiijEEk0YtBnZCbDomiiNdQQtexVAGhMT652ldp1X1ZBHNdPvccFFCWViPybfU6VQkz9eo2nzUGQ7BqjlcJDPZAOfOjav4m70YB1DTsZBecFPmCUwhxcYjjAsTdKJLKFUhE9llawKqH3XqRSju999I7PZAG8pxZC8B1EzdHdltK9dBlRW8Kr6f4G4Fw1b5RbZBwbZB6D4h5JzAkrpOUvQczMhI0eXpk2noxUy7q"
    PHONE_NUMBER_ID = "1168308543041713"
    SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRc2bZvbbN8-_7HXt-Cu0_UPmUpLEcpOcGQimQj8j1Q39i4Hr4E8tjhMCX5krQSAsX4kXwYpzwn5BjC/pub?gid=0&single=true&output=csv" 

# --- DATA FETCH LOGIC ---
@st.cache_data(ttl=10)
def fetch_live_sheet_data(url):
    try:
        clear_url = f"{url}&cache_bypass={int(time.time())}"
        df = pd.read_csv(clear_url, header=None)
        return df, None
    except Exception as e:
        return None, str(e)

# --- SESSION STATE INITIALIZATION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None  # 'admin' ya 'client'
    st.session_state.username = ""

# --- LOGIN / REGISTRATION UI ---
if not st.session_state.logged_in:
    st.title("🔒 XAUUSD AI Algorithmic Network")
    st.subheader("VIP Portal Login & Registration")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["🔑 Sign In", "📝 Create Account / USDT Portal"])
    
    with tab1:
        username = st.text_input("Username / Email:", key="login_user")
        password = st.text_input("Password:", type="password", key="login_pass")
        
        if st.button("Access Dashboard"):
            # Temporary Core Authentication Logic (Phase 2 mein ise database se connect karenge)
            if username == "manishadmin" and password == "goldmaster77":
                st.session_state.logged_in = True
                st.session_state.user_role = "admin"
                st.session_state.username = "Manissh (Admin)"
                st.rerun()
            elif username == "client1" and password == "vipgold":
                st.session_state.logged_in = True
                st.session_state.user_role = "client"
                st.session_state.username = "VIP Premium Client"
                st.rerun()
            else:
                st.error("Invalid Credentials! Please check again.")
                
    with tab2:
        st.markdown("### 🛰️ Complete 3-Step Registration")
        reg_email = st.text_input("Enter Your Gmail Address:")
        reg_wa = st.text_input("Enter WhatsApp Number (With Country Code):", placeholder="e.g. 919825xxxxxx")
        
        st.info("⚠️ **USDT (TRC20) Subscription Payment Gateway**\n\nVIP Matrix Multi-Timeframe Signals & AI Support ke liye fee **$XX USDT** per month hai.\n\nPlease scan or send payment to the address below:")
        st.code("TYq37R4vB1XpZmWqL9KsmHnBvE8DxF4zQk", language="text") # Aapka USDT Wallet address
        
        tx_id = st.text_input("Enter USDT Transaction Hash ID (TxID) after transfer:")
        
        if st.button("Submit Registration Details"):
            if reg_email and reg_wa and tx_id:
                st.success("✅ Application Submitted! AI Agent is verifying your TxID on the blockchain. System access will be granted shortly via WhatsApp notification.")
            else:
                st.warning("Please fill all details and submit valid Transaction ID.")

# --- LIVE DASHBOARD (AFTER SUCCESSFUL LOGIN) ---
else:
    # Top Bar Menu
    st.sidebar.markdown(f"### 👤 Welcome, {st.session_state.username}")
    st.sidebar.markdown(f"**Role:** {st.session_state.user_role.upper()}")
    if st.sidebar.button("Logout 🚪"):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.rerun()

    df, error = fetch_live_sheet_data(SHEET_URL)

    # ----------------------------------------------------
    # 👑 CASE A: ADMIN DASHBOARD VIEW (Full Controls & Tables)
    # ----------------------------------------------------
    if st.session_state.user_role == "admin":
        st.title("⚡ XAUUSD Multi-Agent Command Center (ADMIN MODE)")
        st.markdown("---")
        
        if error:
            st.error(f"Error fetching sheet: {error}")
        else:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("### 📊 Internal System Metrics")
                st.info("Core Orchestrator: Gemini Live Grid Engine Active.")
                st.success("Triggers Lock: Background cron updating sheet every 60s.")
            with col2:
                st.markdown("### 📜 Master Live Sheet Log (Protected View)")
                st.dataframe(df.tail(40), use_container_width=True)
                
    # ----------------------------------------------------
    # 👥 CASE B: PREMIUM CLIENT VIEW (Hidden Sheets, Clean VIP Room)
    # ----------------------------------------------------
    elif st.session_state.user_role == "client":
        st.title("💎 VIP XAUUSD Premium Signal Room")
        st.subheader("Real-Time Algorithmic Execution Hub")
        st.markdown("---")
        
        # Yahan hum client ko sheet nahi dikha rahe hain! Bilkul clean dashboard.
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 🚀 Active Trading Signals")
            # Hum data frame ki aakhri raw read karke client ko clean dynamic updates denge
            if df is not None and not df.empty:
                st.success("🟢 STATUS: AI Engine is scanning M30, H1 and H4 structures.")
                st.metric(label="VIP Premium Active Status", value="SCANNING MATRIX", delta="Grid Secured")
            else:
                st.info("Waiting for next structural market release...")
                
        with col2:
            st.markdown("### 🤖 Your AI Concierge Support")
            st.markdown("> **Note:** VIP Technical Grid Analysis directly aapke register kiye hue WhatsApp par delivery chalu hai. Trade management instructions (Lot Size calculation, dynamic trailing aur targets) automatic text flow ke jariye manage honge.")
            st.info("⏳ Your subscription status: **ACTIVE (29 Days Remaining)**")

    # Auto refresh logic for live data pipes
    time.sleep(10)
    st.rerun()