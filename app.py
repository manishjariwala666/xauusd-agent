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
    st.session_state.user_role = None  
    st.session_state.username = ""

# --- LOGIN / REGISTRATION UI (COMPACT & CENTERED) ---
if not st.session_state.logged_in:
    # 3 Columns banakar beech wali column ko chota (compact) rakha hai
    left_space, center_box, right_space = st.columns([1.2, 1, 1.2])
    
    with center_box:
        st.markdown("<br><br>", unsafe_allow_html=True) # Thoda niche push karne ke liye
        st.markdown("<h2 style='text-align: center;'>🔒 VIP AI Terminal</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Algorithmic Signal Network</p>", unsafe_allow_html=True)
        
        # Chota compact container block
        with st.container(border=True):
            tab1, tab2 = st.tabs(["🔑 Sign In", "📝 USDT Register"])
            
            with tab1:
                # Direct Google/Gmail login click standard look lagane ke liye ek dynamic button mock kiya hai
                if st.button("🔴 Continue with Gmail", use_container_width=True):
                    st.info("Gmail Integration Active: Please type your registered credentials below.")
                
                st.markdown("<div style='text-align: center; margin: 10px 0; color: gray;'>- OR -</div>", unsafe_allow_html=True)
                
                username = st.text_input("Username / Email:", key="login_user", label_visibility="collapsed", placeholder="Email or Username")
                password = st.text_input("Password:", type="password", key="login_pass", label_visibility="collapsed", placeholder="Password")
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Log In", type="primary", use_container_width=True):
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
                        st.error("Invalid Credentials!")
                        
            with tab2:
                reg_email = st.text_input("Gmail Address:", placeholder="yourname@gmail.com")
                reg_wa = st.text_input("WhatsApp Number:", placeholder="919825xxxxxx")
                
                st.markdown("<p style='font-size: 12px; color: gray;'><b>USDT (TRC20) Gateway Address:</b></p>", unsafe_allow_html=True)
                st.code("TYq37R4vB1XpZmWqL9KsmHnBvE8DxF4zQk", language="text")
                
                tx_id = st.text_input("Transaction Hash ID (TxID):", placeholder="Enter TxID after payment")
                
                if st.button("Submit Access Request", use_container_width=True):
                    if reg_email and reg_wa and tx_id:
                        st.success("✅ Submitted! Verification via WhatsApp pending.")
                    else:
                        st.warning("All fields required.")

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

    # ADMIN VIEW
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
                
    # CLIENT VIEW
    elif st.session_state.user_role == "client":
        st.title("💎 VIP XAUUSD Premium Signal Room")
        st.subheader("Real-Time Algorithmic Execution Hub")
        st.markdown("---")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("### 🚀 Active Trading Signals")
            if df is not None and not df.empty:
                st.success("🟢 STATUS: AI Engine is scanning M30, H1 and H4 structures.")
                st.metric(label="VIP Premium Active Status", value="SCANNING MATRIX", delta="Grid Secured")
            else:
                st.info("Waiting for next structural market release...")
        with col2:
            st.markdown("### 🤖 Your AI Concierge Support")
            st.markdown("> **Note:** VIP Technical Grid Analysis directly aapke register kiye hue WhatsApp par delivery chalu hai.")
            st.info("⏳ Your subscription status: **ACTIVE (29 Days Remaining)**")

    time.sleep(10)
    st.rerun()