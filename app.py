import streamlit as st
import pandas as pd
import time
import yfinance as yf
from supabase import create_client, Client

# --- SETTINGS & CONFIG ---
st.set_page_config(page_title="XAUUSD VIP Hub", page_icon="💰", layout="wide")

# Custom CSS for Premium Interface
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
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .status-card {
        background-color: #111827;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #374151;
        margin-bottom: 15px;
    }
    th { background-color: #1f2937 !important; color: #f59e0b !important; font-weight: bold !important; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION ---
SUPABASE_URL = "https://tdgyhqlxoyfkkrhzljwo.supabase.co"
SUPABASE_KEY = "sb_secret_R4xiW5szyOxyrFPRRotsyw_RTiYFWWf"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- GOOGLE SHEET TSV LINK ---
SHEET_TSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRc2bZvbbN8-_7HXt-Cu0_UPmUpLEcpOcGQimQj8j1Q39i4Hr4E8tjhMCX5krQSAsX4kXwYpzwn5BjC/pub?output=tsv"

# --- SESSION STATE INITIALIZATION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# --- LOGIN SCREEN ---
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center; margin-top: 50px;'>🔒 VIP AI Terminal</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Algorithmic Signal Network</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["🔑 Sign In", "📝 Register VIP"])
        
        with tab1:
            email_input = st.text_input("Registered Email ID")
            whatsapp_input = st.text_input("WhatsApp Number", type="password")
            if st.button("Log In", use_container_width=True):
                if email_input == "manishadmin" and whatsapp_input == "goldmaster77":
                    st.session_state.logged_in = True
                    st.session_state.role = "ADMIN"
                    st.session_state.user_email = "Manissh (Admin)"
                    st.rerun()
                else:
                    try:
                        res = supabase.table("users").select("*").eq("email", email_input).eq("whatsapp", whatsapp_input).execute()
                        if len(res.data) > 0:
                            if res.data[0]["status"] == "Approved" or res.data[0].get("status") == "Pending": 
                                st.session_state.logged_in = True
                                st.session_state.role = "USER"
                                st.session_state.user_email = res.data[0]["email"]
                                st.rerun()
                            else:
                                st.error("Your account status is blocked or inactive.")
                        else:
                            st.error("Invalid Email or WhatsApp number.")
                    except Exception as e:
                        st.error("Database Connection Error")
                        
        with tab2:
            reg_email = st.text_input("Enter Email ID")
            reg_whatsapp = st.text_input("WhatsApp Number")
            reg_txid = st.text_input("Transaction ID (TXID)")
            if st.button("Register & Activate Alerts", use_container_width=True):
                if reg_email and reg_whatsapp and reg_txid:
                    try:
                        supabase.table("users").insert({
                            "email": reg_email, 
                            "whatsapp": reg_whatsapp, 
                            "txid": reg_txid,
                            "status": "Pending"
                        }).execute()
                        st.success("Registration Successful!")
                    except Exception as e:
                        st.error("Error during registration.")

# --- APP HUB (LOGGED IN) ---
else:
    st.sidebar.markdown(f"### 👤 Welcome")
    st.sidebar.markdown(f"**Account:** {st.session_state.user_email}")
    st.sidebar.markdown(f"**Role:** {st.session_state.role}")
    if st.sidebar.button("Logout 🚪"):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.user_email = None
        st.rerun()

    st.markdown("<h2 style='color: #f59e0b;'>💰 XAUUSD VIP Signal Hub</h2>", unsafe_allow_html=True)
    st.markdown("---")

    # Fetch Live CMP
    try:
        gold_ticker = yf.Ticker("GC=F")
        raw_price = gold_ticker.history(period="1d")["Close"].iloc[-1]
        calibrated_spot = raw_price - 19.20
        live_price_str = f"${calibrated_spot:.2f}"
    except:
        live_price_str = "Syncing Live Spot Feed..."

    st.markdown(f"<div class='status-card'><span style='color:#10b981;'>●</span> XAUUSD Live Spot CMP: <b>{live_price_str}</b></div>", unsafe_allow_html=True)

    # Fetch Google Sheet Data & Clean Empty Columns
    try:
        df = pd.read_csv(SHEET_TSV_URL, sep="\t")
        # Drop columns that are completely empty or have "Unnamed" and all NaNs
        df = df.dropna(how='all', axis=1)
        # Fill remaining individual NaNs with empty string for clean display
        df = df.fillna("")
        sheet_fetch_success = True
    except:
        sheet_fetch_success = False

    if sheet_fetch_success and not df.empty:
        # Get the absolute latest row
        latest_row = df.iloc[-1]
        
        st.markdown("### 🚨 Latest Premium Signal (Live from Google Sheet)")
        
        # Format the display nicely without printing empty values
        items = []
        for col, val in latest_row.items():
            val_str = str(val).strip()
            if val_str and "Unnamed" not in str(col) and val_str.lower() != "none":
                items.append(f"<b>{col}:</b> {val_str}")
            elif "Unnamed" in str(col) and val_str and val_str.lower() != "none":
                items.append(f"{val_str}")
                
        signal_html = " | &nbsp;&nbsp;&nbsp;&nbsp; ".join(items) if items else "New update logged in sheet."
        
        st.markdown(f"""
        <div class="chat-message-admin">
            <strong>📢 Manissh S Jariwala (Admin Broadcast)</strong><br>
            <p style="font-size: 1.2rem; margin-top: 8px; color: #f3f4f6; line-height: 1.6;">{signal_html}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Display full log history table below
        st.write("")
        st.markdown("### 📊 Historical Signal Logs")
        
        # Filter out completely unnamed or empty columns from dataframe display
        clean_df = df.loc[:, ~df.columns.str.contains('^Unnamed')] if any(df.columns.str.contains('^Unnamed')) else df
        st.dataframe(clean_df.iloc[::-1], use_container_width=True)
        
    else:
        st.info("Waiting for data stream from Google Sheet... Keep this screen open. 🔍")

    if st.button("🔄 Sync & Refresh Sheet Data", use_container_width=True):
        st.rerun()
