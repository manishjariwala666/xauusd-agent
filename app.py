import streamlit as st
import requests
import pandas as pd
import time
from supabase import create_client, Client

# --- SETTINGS & CONFIG ---
st.set_page_config(page_title="XAUUSD VIP Hub", page_icon="💰", layout="wide")

# --- CREDENTIALS & SECRETS CONFIG ---
# Supabase connectivity credentials config
SUPABASE_URL = "https://tdgyhqlxoyfkkrhzljwo.supabase.co"
SUPABASE_KEY = "sb_publishable_R5NjgAUCX8QwrCgrHkyqUw_ijxdBkOs"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Database configuration crash: {str(e)}")

try:
    WHATSAPP_TOKEN = st.secrets["whatsapp"]["token"]
    PHONE_NUMBER_ID = st.secrets["whatsapp"]["phone_number_id"]
    SHEET_URL = st.secrets["google"]["sheet_url"] 
except:
    WHATSAPP_TOKEN = "EAAYmZCZBEO60UBRzJiGJ3kfazGNJeZCutZCPQPzcw9f5TXdZAYwmxjWiijEEk0YtBnZCbDomiiNdQQtexVAGhMT652ldp1X1ZBHNdPvccFFCWViPybfU6VQkz9eo2nzUGQ7BqjlcJDPZAOfOjav4m70YB1DTsZBecFPmCUwhxcYjjAsTdKJLKFUhE9llawKqH3XqRSju999I7PZAG8pxZC8B1EzdHdltK9dBlRW8Kr6f4G4Fw1b5RbZBwbZB6D4h5JzAkrpOUvQczMhI0eXpk2noxUy7q"
    PHONE_NUMBER_ID = "1168308543041713"
    SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRc2bZvbbN8-_7HXt-Cu0_UPmUpLEcpOcGQimQj8j1Q39i4Hr4E8tjhMCX5krQSAsX4kXwYpzwn5BjC/pub?gid=0&single=true&output=csv" 

# --- CUSTOM CSS FOR COMPACT CENTERED LOGIN ---
st.markdown("""
    <style>
    .stAppHeader {display: none;}
    .login-container {
        max-width: 450px;
        margin: 0 auto;
        padding: 30px;
        background-color: #1e1e1e;
        border-radius: 12px;
        border: 1px solid #333333;
        box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.5);
    }
    .main-title { text-align: center; font-size: 26px; font-weight: bold; color: #ffffff; margin-bottom: 5px; }
    .sub-title { text-align: center; font-size: 14px; color: #888888; margin-bottom: 25px; }
    </style>
""", unsafe_allow_html=True)

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

# --- LOGIN / REGISTRATION UI ---
if not st.session_state.logged_in:
    _, center_col, _ = st.columns([1, 1.2, 1])
    
    with center_col:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="main-title">🔒 VIP AI Terminal</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-title">Algorithmic Signal Network</div>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔑 Sign In", "📝 USDT Register"])
        
        with tab1:
            if st.button("🔴 Continue with Gmail", use_container_width=True):
                st.info("Gmail Mapping Active: Please use your credentials below.")
            
            st.markdown("<div style='text-align: center; margin: 15px 0; color: #555;'>- OR -</div>", unsafe_allow_html=True)
            
            username = st.text_input("Username / Email", placeholder="Email or Username", label_visibility="collapsed", key="signin_user")
            password = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed", key="signin_pass")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Log In", type="primary", use_container_width=True):
                # Admin Static Access
                if username == "manishadmin" and password == "goldmaster77":
                    st.session_state.logged_in = True
                    st.session_state.user_role = "admin"
                    st.session_state.username = "Manissh (Admin)"
                    st.rerun()
                else:
                    # Database check for dynamic users
                    try:
                        response = supabase.table("users").select("*").eq("email", username).execute()
                        user_data = response.data
                        
                        if user_data:
                            user_profile = user_data[0]
                            # Dynamic matching using password context or prompt validation
                            if password == "vipgold":  # Default unlock key for valid users
                                if user_profile["status"] == "Active":
                                    st.session_state.logged_in = True
                                    st.session_state.user_role = "client"
                                    st.session_state.username = user_profile["email"]
                                    st.rerun()
                                else:
                                    st.error("⏳ Your account is pending verification! Access locked until admin approval.")
                            else:
                                st.error("❌ Incorrect Password for this profile.")
                        else:
                            st.error("❌ User Profile not found. Please register under USDT tab.")
                    except Exception as err:
                        st.error(f"Auth Network Slow: {str(err)}")
                        
        with tab2:
            reg_email = st.text_input("Gmail Address", placeholder="yourname@gmail.com", key="reg_email")
            reg_wa = st.text_input("WhatsApp Number", placeholder="919825xxxxxx", key="reg_wa")
            
            st.markdown("<p style='font-size: 13px; color: #888; margin-top: 10px;'><b>USDT (TRC20) Address:</b></p>", unsafe_allow_html=True)
            st.code("TYq37R4vB1XpZmWqL9KsmHnBvE8DxF4zQk", language="text")
            
            tx_id = st.text_input("Transaction Hash (TxID)", placeholder="Paste TxID here", key="reg_txid")
            
            if st.button("Submit Registration", use_container_width=True):
                if reg_email and reg_wa and tx_id:
                    # Inserting data directly into Supabase Table
                    try:
                        payload = {"email": reg_email, "whatsapp": reg_wa, "txid": tx_id, "status": "Pending"}
                        supabase.table("users").insert(payload).execute()
                        st.success("✅ Registered Successfully! Data sent to database. Access will be unlocked once verification completes.")
                    except Exception as ins_err:
                        if "already exists" in str(ins_err).lower():
                            st.warning("⚠️ This email is already registered in the system.")
                        else:
                            st.error(f"Database Error: {str(ins_err)}")
                else:
                    st.warning("⚠️ All fields are strictly required.")
                    
        st.markdown('</div>', unsafe_allow_html=True)

# --- LIVE DASHBOARD (AFTER SUCCESSFUL LOGIN) ---
else:
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
        
        # Adding live registered user metrics visibility for Admin
        try:
            db_users = supabase.table("users").select("*").execute()
            user_df = pd.DataFrame(db_users.data)
        except:
            user_df = pd.DataFrame()

        tab_data, tab_users = st.tabs(["📊 Market Live Grid", "👥 User Registrations Portal"])
        
        with tab_data:
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
                    
        with tab_users:
            st.markdown("### 📋 Dynamic Live Registrations from Supabase")
            if not user_df.empty:
                st.dataframe(user_df, use_container_width=True)
            else:
                st.info("No users have registered through the portal yet.")
                
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