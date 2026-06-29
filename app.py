import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- SETTINGS & CONFIG ---
st.set_page_config(page_title="XAUUSD Signal Agent", page_icon="💰", layout="wide")

# Streamlit Secrets se credentials uthane ke liye config
# (Ise hum bad me Streamlit Dashboard dashboard me set karenge)
try:
    WHATSAPP_TOKEN = st.secrets["whatsapp"]["token"]
    PHONE_NUMBER_ID = st.secrets["whatsapp"]["phone_number_id"]
except:
    # Testing ke liye temporary fallback agar secrets configure nahi hain
    WHATSAPP_TOKEN = "EAAYmZCZBEO60UBRzJiGJ3kfazGNJeZCutZCPQPzcw9f5TXdZAYwmxjWiijEEk0YtBnZCbDomiiNdQQtexVAGhMT652ldp1X1ZBHNdPvccFFCWViPybfU6VQkz9eo2nzUGQ7BqjlcJDPZAOfOjav4m70YB1DTsZBecFPmCUwhxcYjjAsTdKJLKFUhE9llawKqH3XqRSju999I7PZAG8pxZC8B1EzdHdltK9dBlRW8Kr6f4G4Fw1b5RbZBwbZB6D4h5JzAkrpOUvQczMhI0eXpk2noxUy7q"
    PHONE_NUMBER_ID = "1168308543041713"

# --- FUNCTIONS ---
def send_whatsapp_alert(signal_type, price):
    """Meta API ke jariye WhatsApp par alert bhejta hai"""
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Meta Test Template: hello_world
    payload = {
        "messaging_product": "whatsapp",
        "to": "91XXXXXXXXXX", # <-- Yahan apna verified WhatsApp number edit karke daal sakte hain
        "type": "template",
        "template": {
            "name": "hello_world",
            "language": {
                "code": "en_US"
            }
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# --- STREAMLIT DASHBOARD UI ---
st.title("💰 XAUUSD Automated Signal Dashboard")
st.subheader("Professional Gold Trading & Automation System")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📊 Market Live Status")
    st.metric(label="Current XAUUSD Price", value="$2,345.50", delta="+12.30 (Bullish)")
    
    # Manual Trigger Testing Button
    if st.button("🚀 Send Test WhatsApp Alert Now"):
        with st.spinner("Sending alert via Meta API..."):
            res = send_whatsapp_alert("BUY", 2345.50)
            if "error" in res:
                st.error(f"Failed to send: {res}")
            else:
                st.success("WhatsApp Alert Sent Successfully!")
                st.json(res)

with col2:
    st.markdown("### 📜 Recent Automated Signals Log")
    mock_data = {
        "Time": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "Asset": ["XAUUSD"],
        "Type": ["BUY"],
        "Entry Price": [2345.50],
        "Status": ["WhatsApp Notified"]
    }
    st.table(pd.DataFrame(mock_data))