import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# --- SETTINGS & CONFIG ---
st.set_page_config(page_title="XAUUSD Command Center", page_icon="💰", layout="wide")

try:
    WHATSAPP_TOKEN = st.secrets["whatsapp"]["token"]
    PHONE_NUMBER_ID = st.secrets["whatsapp"]["phone_number_id"]
    SHEET_URL = st.secrets["google"]["sheet_url"] 
except:
    WHATSAPP_TOKEN = "EAAYmZCZBEO60UBRzJiGJ3kfazGNJeZCutZCPQPzcw9f5TXdZAYwmxjWiijEEk0YtBnZCbDomiiNdQQtexVAGhMT652ldp1X1ZBHNdPvccFFCWViPybfU6VQkz9eo2nzUGQ7BqjlcJDPZAOfOjav4m70YB1DTsZBecFPmCUwhxcYjjAsTdKJLKFUhE9llawKqH3XqRSju999I7PZAG8pxZC8B1EzdHdltK9dBlRW8Kr6f4G4Fw1b5RbZBwbZB6D4h5JzAkrpOUvQczMhI0eXpk2noxUy7q"
    PHONE_NUMBER_ID = "1168308543041713"
    SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT30294631237/pub?output=csv" 

# --- BLOCK-LAYOUT SMART DATA FETCH ---
@st.cache_data(ttl=10)
def fetch_live_sheet_data(url):
    try:
        clear_url = f"{url}&cache_bypass={int(time.time())}"
        # Mixed blocks ko handle karne ke liye simple text dataframe read
        df = pd.read_csv(clear_url, header=None)
        
        # Latest data bottom blocks mein hota hai, isliye last 40 rows pull kar rahe hain
        df_display = df.tail(40) 
        return df_display, None
    except Exception as e:
        return None, str(e)

# --- WHATSAPP NOTIFICATION FUNCTION ---
def send_whatsapp_alert(verified_number):
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": verified_number, 
        "type": "template",
        "template": {
            "name": "hello_world",
            "language": {"code": "en_US"}
        }
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# --- DASHBOARD UI LAYOUT ---
st.title("⚡ XAUUSD Multi-Agent Command Center")
st.subheader("Automated Algorithmic Trading Team & Sheet Pipeline Network")
st.markdown("---")

df, error = fetch_live_sheet_data(SHEET_URL)

if error:
    st.error(f"❌ Google Sheet data fetch karne mein dikkat aayi: {error}")
else:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 📊 Market Status Tracking")
        st.info("System background mein active hai. Har 10 seconds mein sheet ka tail end monitor ho raha hai.")
            
        st.markdown("---")
        st.markdown("### 🎛️ Manual Gateway Testing")
        target_num = st.text_input("Enter Verified WhatsApp Number:", value="919825100000") 
        
        if st.button("🚀 Send Test WhatsApp Alert Now"):
            with st.spinner("Meta API processing..."):
                res = send_whatsapp_alert(target_num)
                if "error" in res:
                    st.error(f"Alert Failed: {res['error']}")
                else:
                    st.success("WhatsApp Template Dispatched!")
                    st.json(res)

    with col2:
        st.markdown("### 📜 Live Sheet View (Bottom Blocks)")
        # Clean standard display bina kisi non-supported parameters ke
        st.dataframe(df, use_container_width=True)

# Dynamic loop auto-refresh
time.sleep(10)
st.rerun()