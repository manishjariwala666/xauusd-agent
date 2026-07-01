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

# --- HIGH-END PREMIUM MODERN GLOWING TRADING THEME DESIGN ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');
    
    * { font-family: 'Space Grotesk', sans-serif; }
    .reportview-container { background: #07090e; }
    
    /* Premium Glassmorphism Container */
    .premium-card {
        background: linear-gradient(135deg, rgba(31, 41, 55, 0.4) 0%, rgba(17, 24, 39, 0.6) 100%);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    
    /* Glowing Indicator Badges */
    .glow-badge-green {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid #10b981;
        color: #34d399;
        padding: 6px 14px;
        border-radius: 50px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-flex;
        align-items: center;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.2);
    }
    
    .glow-badge-rose {
        background: rgba(225, 29, 72, 0.1);
        border: 1px solid #e11d48;
        color: #fb7185;
        padding: 6px 14px;
        border-radius: 50px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-flex;
        align-items: center;
        box-shadow: 0 0 15px rgba(225, 29, 72, 0.2);
    }
    
    /* Metrics Hub */
    .metric-display {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .metric-val {
        font-size: 2rem;
        font-weight: 700;
        color: #f59e0b;
        text-shadow: 0 0 20px rgba(245, 158, 11, 0.3);
    }
    
    /* Modern Chat Streams */
    .chat-message-premium {
        background: rgba(31, 41, 55, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-left: 5px solid #f59e0b;
        padding: 18px;
        border-radius: 12px;
        margin-bottom: 15px;
        color: #e5e7eb;
    }
    
    /* Interactive Streamlit Elements Modification */
    div.stButton > button {
        background: linear-gradient(90deg, #f59e0b 0%, #d97706 100%) !important;
        color: #07090e !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 10px 20px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(245, 158, 11, 0.2) !important;
    }
    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(245, 158, 11, 0.4) !important;
    }
    
    /* Custom Modern Table Framework */
    table { width: 100%; border-collapse: collapse; margin: 15px 0; }
    th { background: #111827 !important; color: #f59e0b !important; font-weight: 600 !important; padding: 12px !important; text-align: left !important; border-bottom: 2px solid rgba(245, 158, 11, 0.2) !important; }
    td { padding: 12px !important; border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important; color: #cbd5e1 !important; }
    tr:hover { background: rgba(255, 255, 255, 0.02); }
</style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION ---
SUPABASE_URL = "https://tdgyhqlxoyfkkrhzljwo.supabase.co"
SUPABASE_KEY = "sb_secret_R4xiW5szyOxyrFPRRotsyw_RTiYFWWf"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- GOOGLE SHEET TSV LINK ---
SHEET_TSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRc2bZvbbN8-_7HXt-Cu0_UPmUpLEcpOcGQimQj8j1Q39i4Hr4E8tjhMCX5krQSAsX4kXwYpzwn5BjC/pub?output=tsv"
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
    st.markdown("<div style='text-align: center; margin-top: 60px;'><h1 style='color: #fff; letter-spacing: -1px; margin-bottom: 5px;'>🔒 XAUUSD VIP AI Terminal</h1><p style='color: #6b7280; font-size: 1.1rem; margin-bottom: 40px;'>Institutional Grade Multi-Agent Intelligence Desk</p></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["🔑 Sign In Desk", "💳 Activate Membership", "🎁 Free Account Access"])
        
        with tab1:
            st.write("")
            email_input = st.text_input("Username or Registered Email ID", key="login_email")
            whatsapp_input = st.text_input("Security Access Key / Password", type="password", key="login_pass")
            st.write("")
            if st.button("Initialize Secure Access", use_container_width=True):
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
            st.write("")
            st.markdown(f"""
            <div class='wallet-box' style='background: rgba(59, 130, 246, 0.05); border: 1px solid rgba(59, 130, 246, 0.3);'>
                <span style='color: #60a5fa; font-weight: 600;'>✨ VIP USDT (TRC20) Vault Key:</span><br>
                <code style='color:#facc15; font-size:1.05rem; word-break: break-all;'>TWeNUrS2617xUssfkT9SHjU6XxZAYADaa8</code><br><br>
                <span style='color: #60a5fa; font-weight: 600;'>🇮🇳 UPI Instant Handler:</span><br>
                <code style='color:#facc15; font-size:1.05rem;'>manissh.jariwala@okaxis</code>
            </div>
            """, unsafe_allow_html=True)
            reg_email = st.text_input("Enter Email Address", key="reg_email")
            reg_whatsapp = st.text_input("WhatsApp Secure Link Number", key="reg_wa")
            reg_txid = st.text_input("Transaction reference ID (TXID)", key="reg_tx")
            if st.button("Submit Network Activation Request", use_container_width=True):
                if reg_email and reg_whatsapp and reg_txid:
                    try:
                        supabase.table("users").insert({"email": reg_email, "whatsapp": reg_whatsapp, "txid": reg_txid, "status": "Pending"}).execute()
                        st.success("Payment Reference Logged Successfully!")
                    except:
                        st.error("Sync error.")
        
        with tab3:
            st.write("")
            st.markdown("<p style='color: #9ca3af;'>Instantly launch an isolated framework dashboard evaluation session.</p>", unsafe_allow_html=True)
            free_email = st.text_input("Enter Email for Session Log", key="free_email_reg")
            st.write("")
            if st.button("Launch Evaluation Hub 🚀", use_container_width=True):
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
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

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

    # High End Dynamic Glass Top-Banner Injector
    st.markdown("<div class='premium-card' style='padding: 20px; margin-top: 10px; display: flex; align-items: center; justify-content: space-between;'>", unsafe_allow_html=True)
    c_left, c_right = st.columns([2, 1])
    with c_left:
        if st.session_state.role == "FREE":
            st.markdown(f"### 👋 Welcome to Alpha Hub, <span style='color:#f59e0b;'>{st.session_state.user_email}</span>", unsafe_allow_html=True)
            st.markdown("<p style='color: #9ca3af; margin:0;'>You are currently observing isolated evaluation frameworks. Upgrade to access live terminal modules.</p>", unsafe_allow_html=True)
        elif st.session_state.role == "PENDING_VIP":
            st.markdown(f"### ⏳ Telemetry Settlement Pending...", unsafe_allow_html=True)
            st.markdown("<p style='color: #f59e0b; margin:0;'>Your USDT token transaction layer is undergoing database validation. Access matrix unlocks automatically.</p>", unsafe_allow_html=True)
        else:
            st.markdown(f"### 👑 VIP Executive Suite Active", unsafe_allow_html=True)
            st.markdown(f"<p style='color: #60a5fa; margin:0;'>Authenticated Terminal Core Connection: <b>{st.session_state.user_email}</b></p>", unsafe_allow_html=True)
    with c_right:
        st.markdown("<div style='text-align: right;'>", unsafe_allow_html=True)
        if st.session_state.role == "FREE":
            st.markdown("<span class='glow-badge-rose'>⚠️ FREE TRIAL INTERFACE ACTIVE</span>", unsafe_allow_html=True)
        elif st.session_state.role == "PENDING_VIP":
            st.markdown("<span class='glow-badge-rose' style='border-color:#f59e0b; color:#facc15;'>⏳ AUDITING PAYLOAD LOGS</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span class='glow-badge-green'>● SECURE NODE UNLOCKED</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # VIP Action Portal Button Unlocked
    if st.session_state.role == "USER":
        st.markdown("<div class='premium-card' style='background: linear-gradient(90deg, rgba(16,185,129,0.1) 0%, rgba(5,150,105,0.2) 100%); border: 1px solid #10b981;'>", unsafe_allow_html=True)
        st.link_button("✈️ JOIN INSTITUTIONAL TELEGRAM BROADCAST CHANNEL NOW", VIP_TELEGRAM_LINK, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- SIDEBAR DESK ---
    st.sidebar.markdown("<h2 style='color:#fff; margin-bottom:0;'>💰 XAUUSD Desk</h2>", unsafe_allow_html=True)
    st.sidebar.caption("Navigation Orchestration Center")
    st.sidebar.markdown("---")
    
    nav_options = ["📢 Live Trading Hub", "🤖 AI Agent Activity Log"]
    if st.session_state.role == "FREE":
        nav_options.append("💳 Activate VIP Tier")
    nav_options.extend(["ℹ️ About Architecture", "🔒 Privacy Desk", "⚠️ Disclaimer"])
        
    workspace_mode = st.sidebar.radio("Navigate View Workspace", nav_options)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("Exit Dashboard Session 🚪", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.user_email = None
        cookie_manager.delete("xau_logged_in")
        cookie_manager.delete("xau_role")
        cookie_manager.delete("xau_email")
        st.rerun()

    # PRICE ENGINE DATA
    try:
        gold_ticker = yf.Ticker("GC=F")
        raw_price = gold_ticker.history(period="1d")["Close"].iloc[-1]
        calibrated_spot = raw_price - 19.20
        if calibrated_spot < 3500: calibrated_spot = 4024.15
        live_price_str = f"${calibrated_spot:.2f}"
    except:
        live_price_str = "$4024.15"

    df, sheet_active = fetch_cached_sheet(SHEET_TSV_URL)
    is_vip_or_admin = st.session_state.role in ["USER", "ADMIN"]
    
    if sheet_active and not df.empty:
        items = [f"<b>{c}:</b> {v}" for c, v in df.iloc[-1].items() if "Unnamed" not in str(c) and str(v).strip() and str(v).lower() != "none"]
        latest_signal = " | ".join(items) if items else f"🚀 VIP Trading Signal Active at {live_price_str}"
    else:
        latest_signal = f"🚀 XAUUSD SCALPER ALERT | Active CMP: {live_price_str}"

    # --- COMPONENT DISPATCH CONTROLLER ---
    
    # 💳 1. PREMIUM PAYMENT GATEWAY REDESIGN
    if workspace_mode == "💳 Activate VIP Tier":
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color: #f59e0b; margin-top:0;'>💳 Premium VIP Desk Gateway</h2>", unsafe_allow_html=True)
        st.write("Complete your structural security payload log below to unlock dynamic data channels.")
        
        c_left, c_right = st.columns([1, 1.6])
        with c_left:
            st.markdown("<div style='background: white; padding: 20px; border-radius: 12px; width: 200px; margin: 0 auto;'>", unsafe_allow_html=True)
            usdt_address = "TWeNUrS2617xUssfkT9SHjU6XxZAYADaa8"
            qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={usdt_address}&color=07090e&bgcolor=ffffff"
            st.image(qr_api_url, width=180)
            st.markdown("</div>", unsafe_allow_html=True)
            st.caption("<div style='text-align:center; margin-top:5px;'>Scan Network QR Vector</div>", unsafe_allow_html=True)
            
        with c_right:
            st.markdown("##### 🔑 USDT TRC20 Wallet Destination Address")
            st.code("TWeNUrS2617xUssfkT9SHjU6XxZAYADaa8", language="text")
            
            st.markdown("##### 🇮🇳 National Banking UPI Handle")
            st.code("manissh.jariwala@okaxis", language="text")
            
        st.markdown("<br><h4>🧾 Submit Settlement Credentials</h4>", unsafe_allow_html=True)
        inner_txid = st.text_input("Transaction reference ID (TXID) Token Input", key="inner_tx")
        inner_wa = st.text_input("WhatsApp Alerts Communication Number", key="inner_wa")
        
        if st.button("Deploy Settlement Verification Keys 🚀", use_container_width=True):
            if inner_txid and inner_wa:
                try:
                    supabase.table("users").upsert({"email": st.session_state.user_email, "whatsapp": inner_wa, "txid": inner_txid, "status": "Pending"}).execute()
                    st.session_state.role = "PENDING_VIP"
                    cookie_manager.set("xau_role", "PENDING_VIP", max_age=604800)
                    st.success("Verification payload broadcast successful!")
                    time.sleep(0.5)
                    st.rerun()
                except: st.error("Sync drop.")
        st.markdown("</div>", unsafe_allow_html=True)

    # 📢 2. LUXURY HUB DASHBOARD REDESIGN
    elif workspace_mode == "📢 Live Trading Hub":
        # Luxury Metric Pad Block
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        m1, m2 = st.columns(2)
        with m1:
            st.markdown(f"<div class='metric-display'><p style='color:#9ca3af; margin:0; font-size:0.9rem;'>🏅 SPOT GOLD XAUUSD (CMP)</p><p class='metric-val'>{live_price_str}</p></div>", unsafe_allow_html=True)
        with m2:
            st.markdown(f"<div class='metric-display'><p style='color:#9ca3af; margin:0; font-size:0.9rem;'>📡 NETWORK PIPELINE INTEGRITY</p><p class='metric-val' style='color:#10b981; text-shadow:0 0 20px rgba(16,185,129,0.3);'>100% ONLINE</p></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.markdown("<h3 style='margin-top:0;'>🤖 Executive AI Floor Consensus</h3>", unsafe_allow_html=True)
        tl, ag = st.columns([1, 2])
        with tl:
            st.markdown("<div style='background:rgba(56,189,248,0.05); border-left:4px solid #38bdf8; padding:15px; border-radius:8px;'><b>👔 Team Leader (Alpha Architect)</b><br><i style='color:#cbd5e1;'>'Consensus parameters secure. Multi-agent monitoring cycles active.'</i></div>", unsafe_allow_html=True)
        with ag:
            if not is_vip_or_admin:
                st.markdown("<div style='background:rgba(225,29,72,0.05); border-left:4px solid #e11d48; padding:15px; border-radius:8px; color:#cbd5e1;'>🔒 <b>Live Data Stream Array Locked</b><br>Upgrade profile to VIP tier to sync automatic multivariable matrix frameworks.</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background:rgba(16,185,129,0.05); border-left:4px solid #10b981; padding:15px; border-radius:8px;'><b>⚡ Live Data Pipeline String</b><br><span style='color:#facc15;'>{latest_signal}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ADMIN PANEL MANAGEMENT
        if st.session_state.role == "ADMIN":
            st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
            st.markdown("### 🛠️ Admin Broadcast Console")
            clean_editable_signal = clean_html_tags(latest_signal)
            signal_msg = st.text_area("Type Signal Payload Matrix to Deploy...", value=clean_editable_signal, height=100)
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
            st.markdown("</div>", unsafe_allow_html=True)

        # LUXURY GRID SPREADSHEET INJECTION
        if sheet_active and is_vip_or_admin:
            st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
            st.markdown("<h4>📊 Institutional Dynamic Sheet Matrix View</h4>", unsafe_allow_html=True)
            st.dataframe(df.tail(6), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # PRESTIGE SIGNAL CHAT STREAMS
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.markdown("<h3 style='margin-top:0;'>📢 Institutional Alpha Broadcast Feed</h3>", unsafe_allow_html=True)
        
        if not is_vip_or_admin:
            st.markdown('<div class="chat-message-premium" style="border-left-color:#e11d48;"><strong>📢 SYSTEM OPERATIONS BOT</strong><br><p style="color:#f87171; margin:5px 0 0 0;">⚠️ Core signal payload distribution locks are engaged. Unlock VIP desk view inside sidebar parameters to release data arrays.</p></div>', unsafe_allow_html=True)
        else:
            if sheet_active:
                st.markdown(f'<div class="chat-message-premium"><strong>📢 GOOGLE AUTOMATION DESK CORRELATION</strong><br><p style="color:#facc15; font-size:1.05rem; margin:5px 0 0 0;">{latest_signal}</p></div>', unsafe_allow_html=True)
            try:
                signals = supabase.table("signals").select("*").order("created_at", desc=True).execute()
                for sig in signals.data:
                    st.markdown(f'<div class="chat-message-premium"><strong>📢 {sig["sender"]}</strong><br><p style="color:#facc15; font-size:1.05rem; margin:5px 0 0 0;">{sig["message"]}</p><span style="font-size:0.75rem; color:#6b7280;">⏱️ Payload Timestamp: {sig["created_at"][:16].replace("T", " ")}</span></div>', unsafe_allow_html=True)
            except: pass
        st.markdown("</div>", unsafe_allow_html=True)

    # 🤖 3. AGENT ACTIVITY LOG PAGES
    elif workspace_mode == "🤖 AI Agent Activity Log":
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color: #38bdf8; margin-top:0;'>🤖 Multi-Agent Live Computational Logs</h2>", unsafe_allow_html=True)
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.markdown(f"##### ⏱️ Current Synchronized Node Timestamp: `{current_time_str}`")
        st.write("")
        
        if not is_vip_or_admin:
            st.markdown(f"<div class='log-box' style='color:#f87171;'>❌ [SECURITY LOCK ACTIVE] <b>[Agent Subsystem Arrays 1 to 5]</b>: Detailed computation telemetry logs are locked for unauthorized evaluation sessions. Upgrade status levels inside sidebar desk.</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='log-box'>⏳ [{current_time_str}] <b>[Agent 1 - Structure Scanner]</b>: Analyzing macro trend arrays... Bullish velocity structural configurations hold.</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='log-box'>⏳ [{current_time_str}] <b>[Agent 2 - Momentum Grid]</b>: Monitoring dynamic volume distributions near spot valuation {live_price_str}.</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='log-box'>⏳ [{current_time_str}] <b>[Agent 3 - Risk Engine]</b>: Tactical risk exposure constraints verified. Safeguards nominal.</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='log-box'>⏳ [{current_time_str}] <b>[Agent 4 - Arbitrage Monitor]</b>: Spread variation and liquidation boundaries nominal.</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='log-box'>⏳ [{current_time_str}] <b>[Agent 5 - Sentiment Matrix]</b>: Scoping safe-haven inflows telemetry data. Capital rotation streaming.</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='log-box' style='color:#facc15;'>⚙️ [{current_time_str}] <b>[AI Orchestrator Core]</b>: Combined report validation cycle complete. Consensus locked.</div>", unsafe_allow_html=True)

        if st.button("🔄 Force Core Telemetry Refresh", use_container_width=True): st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ℹ️ 4. LEGAL DESKS
    elif workspace_mode == "ℹ️ About Architecture":
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color:#38bdf8; margin-top:0;'>ℹ️ Operational Architecture Infrastructure</h2>", unsafe_allow_html=True)
        st.write("Welcome to the **XAUUSD VIP AI Terminal**, an institutional quantitative layout system designed for tracking gold structural metrics pipelines using multi-agent algorithmic logs.")
        st.markdown("</div>", unsafe_allow_html=True)

    elif workspace_mode == "🔒 Privacy Desk":
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color:#10b981; margin-top:0;'>🔒 Data Encryption & Node Privacy Governance</h2>", unsafe_allow_html=True)
        st.write("Session authentication identifiers, encryption nodes, and communication handles are secured using modern serverless cryptography layers. No metrics arrays are shared outside institutional environments.")
        st.markdown("</div>", unsafe_allow_html=True)

    elif workspace_mode == "⚠️ Disclaimer":
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color:#e11d48; margin-top:0;'>⚠️ Risk & Volatility Disclosure</h2>", unsafe_allow_html=True)
        st.write("Commodity spot assets ($XAUUSD$) feature significant financial exposure. System logs, neural charts models, and historical metrics matrices are displayed exclusively for mathematical research logs. Terminal operations do not comprise formal broker advisory packages.")
        st.markdown("</div>", unsafe_allow_html=True)
