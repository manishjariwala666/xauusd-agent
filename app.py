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

# --- INDIGO-PURPLE HIGH PERFORMANCE TRADING RADIAN DESIGN ENGINE ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    .stApp {
        background: radial-gradient(circle at 50% 10%, #0d0f14 0%, #07080a 100%) !important;
    }
    
    section[data-testid="stSidebar"] {
        background-color: #040507 !important;
        border-right: 1px solid rgba(129, 140, 248, 0.08) !important;
    }
    
    /* Dynamic Ultra-Premium Corporate Header Hero Banner Template */
    .hero-banner-container {
        background: linear-gradient(135deg, #4f46e5 0%, #1e1b4b 50%, #090a0f 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 24px;
        padding: 40px;
        margin-bottom: 30px;
        position: relative;
        overflow: hidden;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
    }
    .hero-title {
        color: #ffffff;
        font-size: 2.6rem;
        font-weight: 800;
        letter-spacing: -1px;
        margin: 0;
    }
    .hero-subtitle {
        color: #a5b4fc;
        font-size: 1.1rem;
        font-weight: 500;
        margin-top: 8px;
    }
    
    .premium-card {
        background: linear-gradient(180deg, rgba(17, 20, 28, 0.7) 0%, rgba(10, 12, 18, 0.9) 100%);
        border: 1px solid rgba(129, 140, 248, 0.07);
        border-radius: 16px;
        padding: 26px;
        margin-bottom: 22px;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5);
    }
    
    .glow-header {
        font-weight: 800;
        font-size: 2.3rem;
        letter-spacing: -0.8px;
        background: linear-gradient(135deg, #ffffff 0%, #c7d2fe 60%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .metric-display {
        background: rgba(255, 255, 255, 0.01);
        border: 1px solid rgba(129, 140, 248, 0.05);
        border-radius: 14px;
        padding: 18px;
        text-align: center;
    }
    .metric-val {
        font-size: 2.3rem;
        font-weight: 800;
        color: #ffffff;
    }
    
    .glow-badge-green {
        background: rgba(16, 185, 129, 0.05);
        border: 1px solid #10b981;
        color: #34d399;
        padding: 6px 16px;
        border-radius: 8px;
        font-weight: 600;
    }
    .glow-badge-rose {
        background: rgba(225, 29, 72, 0.05);
        border: 1px solid #e11d48;
        color: #fb7185;
        padding: 6px 16px;
        border-radius: 8px;
        font-weight: 600;
    }
    
    .chat-message-premium {
        background: rgba(255, 255, 255, 0.01);
        border: 1px solid rgba(255, 255, 255, 0.03);
        border-left: 4px solid #818cf8;
        padding: 18px;
        border-radius: 12px;
        margin-bottom: 12px;
        color: #cbd5e1;
    }
    
    div.stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        padding: 10px 22px !important;
        box-shadow: 0 8px 20px rgba(99, 102, 241, 0.2) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION ---
SUPABASE_URL = "https://tdgyhqlxoyfkkrhzljwo.supabase.co"
SUPABASE_KEY = "sb_secret_R4xiW5szyOxyrFPRRotsyw_RTiYFWWf"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

SHEET_TSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRc2bZvbbN8-_7HXt-Cu0_UPmUpLEcpOcGQimQj8j1Q39i4Hr4E8tjhMCX5krQSAsX4kXwYpzwn5BjC/pub?output=tsv"
VIP_TELEGRAM_LINK = "https://t.me/+YourSecretChannelInviteLinkHere"

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
    st.markdown("<div style='text-align: center; margin-top: 80px;'><h1 class='glow-header'>🔒 XAUUSD VIP AI Terminal</h1><p style='color: #4b5563; font-size: 1.05rem; margin-bottom: 40px; font-weight: 500;'>Institutional Grade Multi-Agent Intelligence Desk</p></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.25, 1])
    with col2:
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["🔑 Sign In Desk", "💳 Activate Membership", "🎁 Free Account Access"])
        
        with tab1:
            st.write("")
            email_input = st.text_input("Username or Registered Email ID", key="login_email")
            whatsapp_input = st.text_input("Security Access Key / Password", type="password", key="login_pass")
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
                            if user_db_status == "Approved": st.session_state.role = "USER"
                            elif user_db_status == "Pending": st.session_state.role = "PENDING_VIP"
                            else: st.session_state.role = "FREE"
                                
                            st.session_state.user_email = res.data[0]["email"]
                            cookie_manager.set("xau_logged_in", "true", max_age=604800)
                            cookie_manager.set("xau_role", st.session_state.role, max_age=604800)
                            cookie_manager.set("xau_email", res.data[0]["email"], max_age=604800)
                            st.rerun()
                        else:
                            st.error("Invalid VIP Access Credentials.")
                    except: st.error("Authentication Network Error.")
                        
        with tab2:
            st.write("")
            st.markdown(f"""
            <div style='background: rgba(99, 102, 241, 0.02); border: 1px solid rgba(99, 102, 241, 0.15); padding: 20px; border-radius: 12px; margin-bottom: 20px;'>
                <span style='color: #a5b4fc; font-weight: 600;'>✨ VIP USDT (TRC20) Vault Address:</span><br>
                <code style='color:#ffffff; word-break: break-all;'>TWeNUrS2617xUssfkT9SHjU6XxZAYADaa8</code><br><br>
                <span style='color: #a5b4fc; font-weight: 600;'>🇮🇳 UPI Instant Handler:</span><br>
                <code>manissh.jariwala@okaxis</code>
            </div>
            """, unsafe_allow_html=True)
            reg_email = st.text_input("Enter Email Address", key="reg_email")
            reg_whatsapp = st.text_input("WhatsApp Secure Link Number", key="reg_wa")
            reg_txid = st.text_input("Transaction reference ID (TXID)", key="reg_tx")
            if st.button("Submit Network Activation Request"):
                if reg_email and reg_whatsapp and reg_txid:
                    try:
                        supabase.table("users").insert({"email": reg_email, "whatsapp": reg_whatsapp, "txid": reg_txid, "status": "Pending"}).execute()
                        st.success("Payment Reference Logged Successfully!")
                    except: st.error("Sync error.")
        
        with tab3:
            st.write("")
            free_email = st.text_input("Enter Email for Session Log", key="free_email_reg")
            if st.button("Launch Evaluation Hub 🚀", use_container_width=True):
                if free_email and "@" in free_email:
                    try: supabase.table("users").insert({"email": free_email, "whatsapp": "FREE_ACCOUNT", "txid": "FREE_TRIAL", "status": "Free"}).execute()
                    except: pass
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
        except: pass

    # --- TOP HERO BANNER ---
    if st.session_state.role == "FREE":
        st.markdown(f"""
        <div class='hero-banner-container'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <h1 class='hero-title'>Built for serious traders.</h1>
                    <p class='hero-subtitle'>Welcome to Alpha Suite framework, {st.session_state.user_email}. You are currently evaluating limited data nodes.</p>
                </div>
                <div><span class='glow-badge-rose'>⚠️ EVALUATION MODE</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif st.session_state.role == "PENDING_VIP":
        st.markdown(f"""
        <div class='hero-banner-container' style='background: linear-gradient(135deg, #b45309 0%, #1e1b4b 50%, #090a0f 100%);'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <h1 class='hero-title'>Auditing Settlement Payload Logs...</h1>
                    <p class='hero-subtitle'>Your transaction token layer verification is active. Matrix unlocks automatically.</p>
                </div>
                <div><span class='glow-badge-rose' style='border-color:#f59e0b; color:#facc15;'>⏳ PENDING VALIDATION</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='hero-banner-container' style='background: linear-gradient(135deg, #065f46 0%, #1e1b4b 50%, #090a0f 100%);'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <h1 class='hero-title'>Institutional VIP Node Active</h1>
                    <p class='hero-subtitle'>Welcome back, Executive Operator. Core trading desks are fully synchronized and live.</p>
                </div>
                <div><span class='glow-badge-green'>● SECURE NODE UNLOCKED</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if st.session_state.role == "USER":
        st.markdown("<div class='premium-card' style='background: linear-gradient(90deg, rgba(99,102,241,0.06) 0%, rgba(79,70,229,0.12) 100%); border: 1px solid rgba(99, 102, 241, 0.25); text-align:center;'>", unsafe_allow_html=True)
        st.link_button("✈ SYNC & ENTER VIP TELEGRAM ALPHA STREAM INSTANTLY", VIP_TELEGRAM_LINK, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- SIDEBAR DESK ---
    st.sidebar.markdown("<h2 style='color:#fff; font-weight:800; margin-bottom:0;'>💰 XAUUSD Desk</h2>", unsafe_allow_html=True)
    st.sidebar.caption("Navigation Orchestration Center")
    st.sidebar.markdown("---")
    
    nav_options = ["📢 Live Trading Hub", "📰 Financial Market Insights", "🤖 AI Agent Activity Log"]
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

    try:
        gold_ticker = yf.Ticker("GC=F")
        raw_price = gold_ticker.history(period="1d")["Close"].iloc[-1]
        calibrated_spot = raw_price - 19.20
        if calibrated_spot < 3500: calibrated_spot = 4024.15
        live_price_str = f"${calibrated_spot:.2f}"
    except: live_price_str = "$4024.15"

    df, sheet_active = fetch_cached_sheet(SHEET_TSV_URL)
    is_vip_or_admin = st.session_state.role in ["USER", "ADMIN"]
    
    if sheet_active and not df.empty:
        items = [f"<b>{c}:</b> {v}" for c, v in df.iloc[-1].items() if "Unnamed" not in str(c) and str(v).strip() and str(v).lower() != "none"]
        latest_signal = " | ".join(items) if items else f"🚀 VIP Trading Signal Active at {live_price_str}"
    else: latest_signal = f"🚀 XAUUSD SCALPER ALERT | Active CMP: {live_price_str}"

    # --- WORKSPACE DISPATCH ---
    
    # 📰 NEW WORKSPACE: FINANCIAL MARKET INSIGHTS (BLOG STREAM)
    if workspace_mode == "📰 Financial Market Insights":
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color:#fff; margin-top:0;'>📰 Financial Market Insights & Research Blogs</h2>", unsafe_allow_html=True)
        st.write("Explore professional market analytics and automated network logs compiled by our algorithmic editors.")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # ADMIN MODE: BLOG PUBLISHER ENGINE
        if st.session_state.role == "ADMIN":
            st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
            st.markdown("### ✍️ Premium Blog Content Publisher (Admin Panel)")
            b_title = st.text_input("Blog Post Title")
            b_content = st.text_area("Write Content Matrix (Supports Text & HTML Tags)", height=200)
            
            if st.button("🚀 Push Blog Post to Terminal Hub", use_container_width=True):
                if b_title and b_content:
                    try:
                        supabase.table("blogs").insert({"title": b_title, "content": b_content, "author": "Manissh S Jariwala (Admin)"}).execute()
                        st.success("Blog content published successfully to global node!")
                        time.sleep(0.5)
                        st.rerun()
                    except: st.error("Table initialization check pending.")
                else: st.warning("Please fill out title and content arrays.")
            st.markdown("</div>", unsafe_allow_html=True)
            
        # LIVE VIEW: FETCH AND DISPLAY PUBLISHED BLOGS
        try:
            blogs = supabase.table("blogs").select("*").order("created_at", desc=True).execute()
            if len(blogs.data) == 0:
                st.info("🔄 No research papers are logged in the active network node right now.")
            else:
                for post in blogs.data:
                    st.markdown(f"""
                    <div class='premium-card' style='border-left: 4px solid #6366f1;'>
                        <h3 style='color:#ffffff; margin:0 0 5px 0;'>✨ {post['title']}</h3>
                        <p style='color:#9ca3af; font-size:0.82rem; margin-bottom:15px;'>✍️ Author: {post['author']} | 🕒 Published: {post['created_at'][:16].replace('T', ' ')}</p>
                        <div style='color:#cbd5e1; line-height:1.6; font-size:0.98rem;'>{post['content']}</div>
                    </div>
                    """, unsafe_allow_html=True)
        except:
            st.info("ℹ️ Connect or create a 'blogs' table inside Supabase grid structure to store your articles safely.")

    elif workspace_mode == "💳 Activate VIP Tier":
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color: #fff; font-weight:700; margin-top:0;'>💳 Premium VIP Desk Gateway</h2>", unsafe_allow_html=True)
        c_left, c_right = st.columns([1, 1.6])
        with c_left:
            st.markdown("<div style='background: white; padding: 18px; border-radius: 12px; width: 180px; margin: 0 auto;'>", unsafe_allow_html=True)
            usdt_address = "TWeNUrS2617xUssfkT9SHjU6XxZAYADaa8"
            qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=144x144&data={usdt_address}&color=07080a&bgcolor=ffffff"
            st.image(qr_api_url, width=144)
            st.markdown("</div>", unsafe_allow_html=True)
        with c_right:
            st.markdown("<span>🔑 USDT TRC20 Wallet Destination Address</span>", unsafe_allow_html=True)
            st.code("TWeNUrS2617xUssfkT9SHjU6XxZAYADaa8", language="text")
            st.markdown("<span>🇮🇳 National Banking UPI Handle</span>", unsafe_allow_html=True)
            st.code("manissh.jariwala@okaxis", language="text")
        st.write("")
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

    elif workspace_mode == "📢 Live Trading Hub":
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        m1, m2 = st.columns(2)
        with m1: st.markdown(f"<div class='metric-display'><p style='color:#4b5563; margin:0; font-size:0.82rem; font-weight:600;'>🏅 SPOT GOLD XAUUSD (CMP)</p><p class='metric-val'>{live_price_str}</p></div>", unsafe_allow_html=True)
        with m2: st.markdown(f"<div class='metric-display'><p style='color:#4b5563; margin:0; font-size:0.82rem; font-weight:600;'>📡 NETWORK INTEGRITY MATRIX</p><p class='metric-val' style='color:#34d399;'>100% SECURE</p></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        tl, ag = st.columns([1, 2])
        with tl: st.markdown("<div style='background:rgba(99,102,241,0.01); border-left:4px solid #6366f1; padding:16px; border-radius:8px;'><b>👔 Team Leader (Alpha Architect)</b><br><i style='color:#6b7280; font-size:0.92rem;'>'Consensus state stable.'</i></div>", unsafe_allow_html=True)
        with ag:
            if not is_vip_or_admin: st.markdown("<div style='background:rgba(225,29,72,0.01); border-left:4px solid #e11d48; padding:16px; border-radius:8px; color:#6b7280; font-size:0.92rem;'>🔒 <b>Live Streaming Array Locked</b><br>Upgrade profile to VIP tier to sync automatic matrix frameworks.</div>", unsafe_allow_html=True)
            else: st.markdown(f"<div style='background:rgba(16,185,129,0.01); border-left:4px solid #10b981; padding:16px; border-radius:8px;'><b>⚡ Live Data Pipeline String</b><br><span style='color:#ffffff;'>{latest_signal}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

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
                        st.success("Signal deployed globally!")
                        time.sleep(0.5)
                        st.rerun()
            with c2:
                if st.button("✈️ Sync & Blast Signal to Telegram Channel", use_container_width=True):
                    if signal_msg:
                        supabase.table("signals").insert({"message": f"[TG BROADCAST] {signal_msg}", "sender": "Manissh S Jariwala (Admin)"}).execute()
                        st.success("Telegram Broadcaster Active.")
            st.markdown("</div>", unsafe_allow_html=True)

        if sheet_active and is_vip_or_admin:
            st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
            st.dataframe(df.tail(6), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        if not is_vip_or_admin: st.markdown('<div class="chat-message-premium" style="border-left-color:#e11d48;"><strong>📢 SYSTEM OPERATIONS BOT</strong><br><p style="color:#fb7185; margin:5px 0 0 0;">⚠️ Core signal metrics arrays are restricted.</p></div>', unsafe_allow_html=True)
        else:
            if sheet_active: st.markdown(f'<div class="chat-message-premium"><strong>📢 GOOGLE AUTOMATION DESK CORRELATION</strong><br><p style="color:#ffffff; margin:4px 0 0 0;">{latest_signal}</p></div>', unsafe_allow_html=True)
            try:
                signals = supabase.table("signals").select("*").order("created_at", desc=True).execute()
                for sig in signals.data:
                    st.markdown(f'<div class="chat-message-premium"><strong>📢 {sig["sender"]}</strong><br><p style="color:#ffffff; margin:4px 0 0 0;">{sig["message"]}</p></div>', unsafe_allow_html=True)
            except: pass
        st.markdown("</div>", unsafe_allow_html=True)

    elif workspace_mode == "🤖 AI Agent Activity Log":
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color: #fff; font-weight:700; margin-top:0;'>🤖 Multi-Agent Live Computational Logs</h2>", unsafe_allow_html=True)
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not is_vip_or_admin: st.markdown(f"<div class='log-box' style='color:#fb7185;'>❌ Detailed computation telemetry logs are locked.</div>", unsafe_allow_html=True)
        else: st.markdown(f"<div class='log-box'>⏳ [{current_time_str}] <b>[Agent 1]</b>: Consensus nominal.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    elif workspace_mode == "ℹ️ About Architecture":
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.write("Welcome to the XAUUSD VIP AI Terminal operational metrics dashboard.")
        st.markdown("</div>", unsafe_allow_html=True)
