import streamlit as st
import pandas as pd
import time
import yfinance as yf
from supabase import create_client, Client

# --- SETTINGS & CONFIG ---
st.set_page_config(page_title="XAUUSD VIP Hub", page_icon="💰", layout="wide")

# Custom CSS for Premium Chat Interface
st.markdown("""
<style>
    .reportview-container { background: #0e1117; }
    .chat-message-admin {
        background-color: #1f2937;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border-left: 5px solid #f59e0b;
        color: #f3f4f6;
    }
    .chat-time { font-size: 0.8rem; color: #9ca3af; margin-top: 5px; }
    .status-card {
        background-color: #111827;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #374151;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION ---
SUPABASE_URL = "https://tdgyhqlxoyfkkrhzljwo.supabase.co"
SUPABASE_KEY = "sb_secret_R4xiW5szyOxyrFPRRotsyw_RTiYFWWf"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
            whatsapp_input = st.text_input("WhatsApp Number", type="password", help="Enter your registered whatsapp number as password")
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
            reg_whatsapp = st.text_input("WhatsApp Number (with country code)")
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
                        st.success("Registration Successful! Status: Pending Approval.")
                    except Exception as e:
                        st.error("Email already registered or database structure mismatch.")
                else:
                    st.warning("Please fill all details.")

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

    # Fetching Live Gold CMP from yfinance and applying terminal sync math
    try:
        gold_ticker = yf.Ticker("GC=F")
        raw_price = gold_ticker.history(period="1d")["Close"].iloc[-1]
        # Mathematical Terminal Offset Calibration (-$19.20 point synchronization)
        calibrated_spot = raw_price - 19.20
        live_price_str = f"${calibrated_spot:.2f}"
    except:
        live_price_str = "Syncing Live Spot Feed..."

    if st.session_state.role == "ADMIN":
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### 🛠️ Admin Control Panel")
            st.markdown(f"<div class='status-card'><span style='color:#10b981;'>●</span> XAUUSD Live Spot CMP: <b>{live_price_str}</b></div>", unsafe_allow_html=True)
            st.write("")
            
            st.markdown("#### 📣 Broadcast New Signal / Message")
            signal_msg = st.text_area("Type your XAUUSD Signal here...", height=150, placeholder="Example:\n🚀 XAUUSD BUY NOW\nEntry: 2320 - 2322\nTP: 2335 | SL: 2310")
            
            if st.button("🚀 Broadcast to Users", use_container_width=True):
                if signal_msg:
                    try:
                        supabase.table("signals").insert({"message": signal_msg, "sender": "Manissh (Admin)"}).execute()
                        st.success("Signal broadcasted successfully!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Database Error: {e}")
                else:
                    st.warning("Please enter a message first.")
        
        with col2:
            st.markdown("### 📱 Live Broadcast Feed (What Users See)")
            try:
                signals = supabase.table("signals").select("*").order("created_at", desc=True).execute()
                if len(signals.data) == 0:
                    st.info("No signals broadcasted yet.")
                else:
                    for sig in signals.data:
                        st.markdown(f"""
                        <div class="chat-message-admin">
                            <strong>📢 {sig['sender']}</strong><br>
                            <p style="white-space: pre-wrap; margin-top: 5px;">{sig['message']}</p>
                            <div class="chat-time">🕒 {sig['created_at'][:16].replace('T', ' ')}</div>
                        </div>
                        """, unsafe_allow_html=True)
            except Exception as e:
                st.markdown('<div class="chat-message-admin"><strong>📢 Manissh (Admin)</strong><br><p style="white-space: pre-wrap; margin-top: 5px;">🚀 Live Feed Engine Active.<br>Waiting for data flow.</p></div>', unsafe_allow_html=True)

    elif st.session_state.role == "USER":
        st.markdown(f"### 📢 Live VIP Signal Stream | <span style='color:#f59e0b;'>Gold Spot CMP: {live_price_str}</span>", unsafe_allow_html=True)
        st.caption("Real-time algorithmic trading updates from Admin.")
        
        try:
            signals = supabase.table("signals").select("*").order("created_at", desc=True).execute()
            if len(signals.data) == 0:
                st.info("Waiting for the next premium XAUUSD signal... Keep this screen open. 🔍")
            else:
                for sig in signals.data:
                    st.markdown(f"""
                    <div class="chat-message-admin">
                        <strong>📢 {sig['sender']}</strong><br>
                        <p style="white-space: pre-wrap; margin-top: 5px;">{sig['message']}</p>
                        <div class="chat-time">🕒 {sig['created_at'][:16].replace('T', ' ')}</div>
                    </div>
                    """, unsafe_allow_html=True)
        except Exception as e:
            st.warning("Awaiting live signals from admin dashboard...")
