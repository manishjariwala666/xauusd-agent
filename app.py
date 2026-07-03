import streamlit as st

# Session state initialize karein
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

def login_page():
    st.title("🔒 Institutional Access")
    password = st.text_input("Enter VIP Node Key", type="password")
    if st.button("Access Desk"):
        if password == "YOUR_SECRET_KEY": # Yahan apna password rakhein
            st.session_state['authenticated'] = True
            st.rerun()
        else:
            st.error("Invalid Node Key")

# MAIN LOGIC
if not st.session_state['authenticated']:
    login_page()
else:
    # Yahan aapka dashboard code aayega (jo abhi live hai)
    render_dashboard()
