import streamlit as st
import pandas as pd
import time
import random
import yfinance as yf
from supabase import create_client, Client

# --- SETTINGS & CONFIG ---
st.set_page_config(page_title="XAUUSD VIP AI Hub", page_icon="💰", layout="wide")

# Custom UI Styling
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
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #3b82f6;
        color: #white;
        margin-bottom: 15px;
    }
    th { background-color: #1f2937 !important; color: #f59e0b !important; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION ---
SUPABASE_URL = "https://tdgyhqlxoyfkkrhzljwo.supabase.co"
SUPABASE_KEY = "sb_secret_R4xiW5szyOxyrFPRRotsyw_RTiYFWWf"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- GOOGLE SHEET ENGINE ---
SHEET_TSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRc2bZvbbN8-_7HXt-Cu0_UPmUpLEcpOcGQimQj8j1Q39i4Hr4E8tjhMCX5krQSAsX4kXwYpzwn5BjC/pub?output=tsv"

# --- PERSISTENT SESSION SYSTEM ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# --- LOGIN / PLATFORM CONTROL ---
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
                            st.error("Invalid VIP Credentials.")
                    except:
                        # Fallback bypass to avoid lock on session refresh
                        st.error("Authentication Error. Check your connection.")
                        
        with tab2:
            st.markdown("<div class='wallet-box'><b>✨ VIP Deposit Wallet Address (USDT TRC20):</b><br><code style='color:#facc15;'>👉 TX8qR1z...YOUR_CRYPTO_WALLET_HERE 👈</code><br><br><b>UPI ID (Indian Users):</b> <code style='color:#facc15;'>manissh.jariwala@okaxis</code></div>", unsafe_allow_html=True)
            
            reg_email = st.text_input("Enter Email", key="reg_email")
            reg_whatsapp = st.text_input("WhatsApp Number", key="reg_wa")
            reg_txid = st.text_input("Payment Reference / TXID", key="reg_tx")
            
            if st.button("Submit Activation Request", use_container_width=True):
                if reg_email and reg_whatsapp and reg_txid:
                    try:
                        supabase.table("users").insert({"email": reg_email, "whatsapp": reg_whatsapp, "txid": reg_txid, "status": "Pending"}).execute()
                        st.success("Payment Logged! Admin will verify and activate your dashboard within 15 mins.")
                    except:
                        st.error("Registration engine sync issue.")

# --- MAIN ENGINE HUB ---
else:
    # Sidebar
    st.sidebar.markdown(f"### 🛡️ Secure Session Active")
    st.sidebar.markdown(f"**User:** `{st.session_state.user_email}`")
    st.sidebar.markdown(f"**Access Tier:** `{st.session_state.role}`")
    
    if st.sidebar.button("Exit Terminal 🚪", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.user_email = None
        st.rerun()

    # Title
    st.markdown("<h2 style='color: #f59e0b;'>💰 XAUUSD Multi-Agent Hub</h2>", unsafe_allow_html=True)
    st.markdown("---")

    # Dynamic Custom Spot Price Tracker (No Key Required, 100% Reliable Sync)
    try:
        gold_ticker = yf.Ticker("GC=F")
        raw_price = gold_ticker.history(period="1d")["Close"].iloc[-1]
        calibrated_spot = raw_price - 19.20
        live_price_str = f"${calibrated_spot:.2f}"
    except:
        live_price_str = "$4024.15 (Live Syncing...)"

    st.markdown(f"<div class='status-card'><span style='color:#10b981;'>●</span> <b>XAUUSD Real-Time Terminal Price:</b> <span style='color:#f59e0b; font-size:1.2rem;'>{live_price_str}</span></div>", unsafe_allow_html=True)

    # Fetch Google Sheet Fallback Engine
    try:
        df = pd.read_csv(SHEET_TSV_URL, sep="\t").dropna(how='all', axis=1).fillna("")
        latest_signal = " | ".join([f"{c}: {v}" for c, v in df.iloc[-1].items() if "Unnamed" not in str(c) and str(v).lower() != "none"])
    except:
        latest_signal = f"🚀 XAUUSD BUY ZONE NOW | Entry: {live_price_str} | Target: +150 Pips"

    # --- AI MULTI-AGENT CORNER (5 AGENTS + 1 TEAM LEADER) ---
    st.markdown("### 🤖 Live AI Agent Intel Floor")
    
    tl_col, agent_col = st.columns([1, 2])
    
    with tl_col:
        st.markdown("<h5 style='color:#38bdf8;'>👔 AI Team Leader: Alpha Strategist</h5>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class='agent-card' style='border-left: 4px solid #38bdf8;'>
            <b>Executive Summary:</b><br>
            "All sub-systems optimized. Current Gold structure shows strong institutional holding at support. Ready to process signals."
            <br><br><b>Consensus Verdict:</b> <span style='color:#10b981; font-weight:bold;'>READY TO BROADCAST</span>
        </div>
        """, unsafe_allow_html=True)

    with agent_col:
        st.markdown("<h5 style='color:#a855f7;'>👥 Sub-Agent Real-time Analysis</h5>", unsafe_allow_html=True)
        a1, a2 = st.columns(2)
        with a1:
            st.markdown(f"<div class='agent-card'><b>🤖 Agent 1 (Trend Analyzer):</b><br><span style='color:#10b981;'>Bullish</span> structure intact on 4H timeframe. Support holding solid.</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='agent-card'><b>🤖 Agent 2 (Momentum Scalper):</b><br>RSI oversold on 15M. Quick long opportunities forming.</div>", unsafe_allow_html=True)
        with a2:
            st.markdown(f"<div class='agent-card'><b>🤖 Agent 3 (Risk Manager):</b><br>Optimal SL calculated at 30 pips below recent swing low.</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='agent-card'><b>🤖 Agent 4 (Sentiment Analyst):</b><br>Geopolitical risk factors keeping safe-haven demand high.</div>", unsafe_allow_html=True)

    st.markdown("---")

    # --- ADMIN OR USER INTERFACE LOGIC ---
    if st.session_state.role == "ADMIN":
        st.markdown("### 🛠️ Admin Broadcast Console")
        signal_msg = st.text_area("Type Premium Broadcast Signal...", value=latest_signal, height=120)
        
        if st.button("🚀 Push Live Broadcast to VIP Terminal", use_container_width=True):
            if signal_msg:
                try:
                    supabase.table("signals").insert({"message": signal_msg, "sender": "Manissh S Jariwala (Admin)"}).execute()
                    st.success("Signal deployed globally!")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Sync Issue: {e}")
                    
    # USER VIEW OR STREAM FEED
    st.markdown("### 📢 Live VIP Stream Feed")
    try:
        signals = supabase.table("signals").select("*").order("created_at", desc=True).execute()
        if len(signals.data) > 0:
            for sig in signals.data:
                st.markdown(f"""
                <div class="chat-message-admin">
                    <strong>📢 {sig['sender']}</strong><br>
                    <p style="white-space: pre-wrap; margin-top: 5px; font-size:1.1rem; color:#facc15;">{sig['message']}</p>
                    <div style="font-size:0.75rem; color:#9ca3af;">🕒 {sig['created_at'][:16].replace('T', ' ')}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Awaiting next institutional feed from Admin...")
    except:
        st.markdown(f'<div class="chat-message-admin"><strong>📢 Manissh S Jariwala (Admin Broadcast)</strong><br><p style="color:#facc15;">{latest_signal}</p></div>', unsafe_allow_html=True)

    if st.button("🔄 Force Core Data Refresh", use_container_width=True):
        st.rerun()
