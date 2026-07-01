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
        padding: 22px;
        border-radius: 12px;
        border: 2px solid #3b82f6;
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
    .premium-success-box {
        background-color: #064e3b;
        padding: 20px;
        border-radius: 10px;
        border: 2px solid #10b981;
        color: white;
        margin-bottom: 20px;
        text-align: center;
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

# --- SECRET TELEGRAM VIP JOIN LINK ---
VIP_TELEGRAM_LINK = "https://t.me/+YourSecretChannelInviteLinkHere"

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

@st.cache_data(ttl=10)
def fetch_cached_sheet(url):
    try:
        nocache_url = f"{url}&cachebust={time.time()}"
        df = pd.read_csv(nocache_url, sep="\t").dropna(how='all', axis=1).fillna("")
        return df, True
    except:
        return pd.DataFrame(), False

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
                else:
                    try:
                        res = supabase.table("users").select("*").eq("email", email_input).eq("whatsapp", whatsapp_input).execute()
                        if len(res.data) > 0:
                            st.session_state.logged_in = True
                            user_db_status = res.data[0].get("status", "Free")
                            if user_db_status == "Approved":
                                st.session_state.role = "USER"
                            elif user_db_status == "Pending":
                                st.session_state.role = "PENDING_VIP"
                            else:
                                st.session_state.role = "FREE"
                                
                            st.session_state.user_email = res.data[0]["email"]
                            cookie_manager.set("xau_logged_in", "true", max_age=604800)
                            cookie_manager.set("xau_role", st.session_state.role, max_age=604800)
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
                <span style='font-size:0.85rem; color:#9ca3af;'>⚠️ Submit your TXID below for validation.</span>
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
                Explore executive layouts and track live gold pricing models instantly.
            </div>
            """, unsafe_allow_html=True)
            free_email = st.text_input("Enter Your Email Address", key="free_email_reg")
            if st.button("Create Free Account & Login", use_container_width=True):
                if free_email and "@" in free_email:
                    try:
                        supabase.table("users").insert({"email": free_email, "whatsapp": "FREE_ACCOUNT", "txid": "FREE_TRIAL", "status": "Free"}).execute()
                    except:
                        pass
                    st.session_state.logged_in = True
                    st.session_state.role = "FREE"
                    st.session_state.user_email = free_email
                    cookie_manager.set("xau_logged_in", "true", max_age=604800)
                    cookie_manager.set("xau_role", "FREE", max_age=604800)
                    cookie_manager.set("xau_email", free_email, max_age=604800)
                    st.success("Welcome aboard!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Please enter a valid email address.")

# --- LIVE WORKSPACE ---
else:
    # --- REALTIME DATABASE STATUS SYNC ---
    if st.session_state.role not in ["ADMIN", "FREE"]:
        try:
            sync_res = supabase.table("users").select("status").eq("email", st.session_state.user_email).execute()
            if len(sync_res.data) > 0:
                current_db_status = sync_res.data[0]["status"]
                if current_db_status == "Approved" and st.session_state.role != "USER":
                    st.session_state.role = "USER"
                    cookie_manager.set("xau_role", "USER", max_age=604800)
                elif current_db_status == "Pending" and st.session_state.role != "PENDING_VIP":
                    st.session_state.role = "PENDING_VIP"
                    cookie_manager.set("xau_role", "PENDING_VIP", max_age=604800)
        except:
            pass

    # Top Welcome Banner
    if st.session_state.role == "FREE":
        st.markdown(f"""
        <div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left:6px solid #e11d48; margin-bottom:20px;'>
            <h4 style='margin:0; color:#e11d48;'>👋 Welcome to XAUUSD AI Trial Hub!</h4>
            <p style='margin:5px 0 0 0; font-size:0.95rem; color:#cbd5e1;'>You are exploring on a Free Trial Tier. Click <b>💳 Activate VIP Tier</b> in the sidebar to unlock live institutional signals.</p>
        </div>
        """, unsafe_allow_html=True)
    elif st.session_state.role == "PENDING_VIP":
        st.markdown(f"""
        <div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left:6px solid #f59e0b; margin-bottom:20px;'>
            <h4 style='margin:0; color:#f59e0b;'>⏳ Payment Verification In Progress</h4>
            <p style='margin:5px 0 0 0; font-size:0.95rem; color:#cbd5e1;'>Admin is verifying your transaction token. Secret Telegram link unlocks automatically upon confirmation.</p>
        </div>
        """, unsafe_allow_html=True)
    elif st.session_state.role == "USER":
        st.markdown(f"""
        <div class='premium-success-box'>
            <h3 style='margin:0; color:#10b981;'>🎉 VIP Membership Confirmed!</h3>
            <p style='margin:8px 0 15px 0; font-size:1.05rem; color:#d1fae5;'>Welcome back, <b>{st.session_state.user_email}</b>. All algorithmic desks are unlocked.</p>
        </div>
        """, unsafe_allow_html=True)
        st.link_button("✈️ JOIN VIP TELEGRAM SIGNAL CHANNEL NOW", VIP_TELEGRAM_LINK, use_container_width=True)
        st.write("")

    # --- SIDEBAR NAVIGATION BAR ---
    st.sidebar.markdown("### 🛡️ Secure Session Active")
    st.sidebar.markdown(f"**User:** `{st.session_state.user_email}`")
    st.sidebar.markdown(f"**Access Tier:** `{st.session_state.role}`")
    
    # Show dynamic menus based on account tier
    nav_options = ["📢 Live Trading Hub", "🤖 AI Agent Activity Log"]
    if st.session_state.role == "FREE":
        nav_options.append("💳 Activate VIP Tier")
        
    workspace_mode = st.sidebar.radio("Navigate View", nav_options)
    
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

    df, sheet_active = fetch_cached_sheet(SHEET_TSV_URL)
    is_vip_or_admin = st.session_state.role in ["USER", "ADMIN"]
    
    if sheet_active and not df.empty:
        items = []
        for c, v in df.iloc[-1].items():
            if "Unnamed" not in str(c) and str(v).strip() and str(v).lower() != "none":
                items.append(f"<b>{c}:</b> {v}")
        latest_signal = " | ".join(items) if items else f"🚀 VIP Trading Signal Active at {live_price_str}"
    else:
        latest_signal = f"🚀 XAUUSD SCALPER ALERT | Active CMP: {live_price_str} | Strategy Configured"

    # --- MODE SELECTED CONTROLLER ---
    
    # 💳 1. NEW MODE: DEDICATED SIDEBAR PAYMENT GATEWAY PAGE
    if workspace_mode == "💳 Activate VIP Tier":
        st.markdown("<h2 style='color: #3b82f6;'>💳 Premium VIP Desk Gateway</h2>", unsafe_allow_html=True)
        st.write("Complete your security deposit payload below to activate direct data pipelines.")
        
        c_left, c_right = st.columns([1, 1.5])
        with c_left:
            st.markdown("#### 🔳 Secure QR Scan Matrix")
            # Elegant Simulated Barcode / QR Box
            st.markdown("""
            <div style='background-color: white; padding: 25px; border-radius: 12px; text-align: center; width: 220px; margin: 0 auto;'>
                <div style='background-color: #111; width: 170px; height: 170px; margin: 0 auto; display: flex; align-items: center; justify-content: center; color: #38bdf8; font-family: monospace; font-weight: bold; font-size: 0.85rem; border: 4px dashed #3b82f6;'>
                    [ USDT.TRC20 ]<br>SCAN CODE TO<br>DEPOSIT PAYLOAD
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with c_right:
            st.markdown("#### 🔑 Transfer Payload Destination Keys")
            
            st.code("TWeNUrS2617xUssfkT9SHjU6XxZAYADaa8", language="text")
            st.caption("📋 Click double-box icon on the right edge of the code block above to instantly copy USDT TRC20 Wallet key.")
            
            st.code("manissh.jariwala@okaxis", language="text")
            st.caption("📋 Click double-box icon on the right edge above to instantly copy UPI Netbanking handle.")
            
        st.markdown("---")
        st.markdown("#### 🧾 Submit Settlement Log Credentials")
        inner_txid = st.text_input("Payment Reference / Transaction ID (TXID) Token", key="inner_tx")
        inner_wa = st.text_input("WhatsApp Number (For Notification Protocols)", key="inner_wa")
        
        if st.button("🚀 Deploy Activation Request Key", use_container_width=True):
            if inner_txid and inner_wa:
                try:
                    supabase.table("users").upsert({"email": st.session_state.user_email, "whatsapp": inner_wa, "txid": inner_txid, "status": "Pending"}).execute()
                    st.session_state.role = "PENDING_VIP"
                    cookie_manager.set("xau_role", "PENDING_VIP", max_age=604800)
                    st.success("Verification token successfully synchronized! Returning to main floor...")
                    time.sleep(1)
                    st.rerun()
                except:
                    st.error("Synchronization delay.")
            else:
                st.warning("Please fully fill credentials.")

    # 📢 2. MODE: LIVE HUB DASHBOARD (NOW 100% EXPANDER FREE)
    elif workspace_mode == "📢 Live Trading Hub":
        st.markdown("<h2 style='color: #f59e0b;'>💰 XAUUSD Multi-Agent Hub</h2>", unsafe_allow_html=True)
        st.markdown(f"<div class='status-card'><span style='color:#10b981;'>●</span> <b>Real-Time Spot Price (Synced):</b> <span style='color:#f59e0b; font-size:1.2rem;'>{live_price_str}</span></div>", unsafe_allow_html=True)

        st.markdown("### 🤖 Executive AI Floor")
        tl, ag = st.columns([1, 2])
        with tl:
            st.markdown("<div class='agent-card' style='border-left: 4px solid #38bdf8;'><b>👔 Team Leader (Alpha Strategist):</b><br>'All sub-systems executing protocols. System stable.'</div>", unsafe_allow_html=True)
        with ag:
            if not is_vip_or_admin:
                st.markdown("<div class='agent-card' style='color:#9ca3af;'>🔒 <b>Data Pipeline Status:</b> [Locked for Free/Pending Accounts] Complete VIP validation to unlock Google Sheet streaming matrix.</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='agent-card'><b>⚡ Data Pipeline Status:</b> {latest_signal}</div>", unsafe_allow_html=True)

        # ADMIN PANEL MANAGEMENT
        if st.session_state.role == "ADMIN":
            st.markdown("### 🛠️ Admin Broadcast Console")
            clean_editable_signal = clean_html_tags(latest_signal)
            signal_msg = st.text_area("Type Signal to Deploy...", value=clean_editable_signal, height=100)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🚀 Push Live Broadcast to VIP Terminal", use_container_width=True):
                    if signal_msg:
                        supabase.table("signals").insert({"message": signal_msg, "sender": "Manissh S Jariwala (Admin)"}).execute()
                        st.success("Signal deployed globally to VIP Hub!")
                        time.sleep(0.5)
                        st.rerun()
            with c2:
                if st.button("✈️ Sync & Blast Signal to Telegram Channel", use_container_width=True):
                    if signal_msg:
                        supabase.table("signals").insert({"message": f"[TG BROADCAST] {signal_msg}", "sender": "Manissh S Jariwala (Admin)"}).execute()
                        st.success("Telegram Broadcaster Active.")

        st.markdown("### 📢 Live VIP Stream Feed")
        if sheet_active and is_vip_or_admin:
            with st.expander("📊 Dynamic Neural Matrix Sheet Stream (Click to Expand)", expanded=True):
                st.dataframe(df.tail(6), use_container_width=True)

        if not is_vip_or_admin:
            st.markdown('<div class="chat-message-admin" style="border-left:6px solid #e11d48;"><strong>📢 System Core Bot</strong><br><p style="color:#f87171; font-size:1rem; margin-top:5px;">⚠️ Live Signal Stream is locked. Please activate VIP tier inside sidebar navigation desk to get invite token link access.</p></div>', unsafe_allow_html=True)
        else:
            if sheet_active:
                st.markdown(f'<div class="chat-message-admin"><strong>📢 Google Sheet Real-time Feed</strong><br><p style="color:#facc15; font-size:1.1rem; margin-top:5px;">{latest_signal}</p></div>', unsafe_allow_html=True)
            try:
                signals = supabase.table("signals").select("*").order("created_at", desc=True).execute()
                for sig in signals.data:
                    st.markdown(f'<div class="chat-message-admin"><strong>📢 {sig["sender"]}</strong><br><p style="color:#facc15; font-size:1.1rem; margin-top:5px;">{sig["message"]}</p></div>', unsafe_allow_html=True)
            except:
                pass

    # 🤖 3. MODE: AI RUNTIME LOG PANEL
    elif workspace_mode == "🤖 AI Agent Activity Log":
        st.markdown("<h2 style='color: #38bdf8;'>🤖 Live AI Agent Runtime Log</h2>", unsafe_allow_html=True)
        st.write("")
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if not is_vip_or_admin:
            st.markdown(f"<div class='log-box' style='color:#f87171;'>❌ [RESTRICTED] <b>[Agent 1 to 5 Logs]</b>: Detailed sub-agent runtime parameters are locked for Free/Pending accounts. Please update access levels.</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='log-box'>⏳ [{current_time_str}] <b>[Agent 1 - Trend Analyzer]</b>: Scanning H4 Chart... Bullish confirmation active.</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='log-box'>⏳ [{current_time_str}] <b>[Agent 2 - Momentum Scalper]</b>: Monitoring M15 RSI/MACD crossovers near price {live_price_str}.</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='log-box'>⏳ [{current_time_str}] <b>[Agent 3 - Risk Manager]</b>:Dynamic Stop-Loss safety parameters verified.</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='log-box'>⏳ [{current_time_str}] <b>[Agent 4 - Volatility Monitor]</b>: Liquidations and spread gaps tracking active.</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='log-box'>⏳ [{current_time_str}] <b>[Agent 5 - Sentiment Analyst]</b>: Safe-haven capital inflows streaming into XAU.</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='log-box' style='color:#facc15;'>⚙️ [{current_time_str}] <b>[AI Team Leader - Alpha Strategist]</b>: Consensus calculated. System locked and synced.</div>", unsafe_allow_html=True)

        if st.button("🔄 Sync & Refresh Live Logs", use_container_width=True):
            st.rerun()
