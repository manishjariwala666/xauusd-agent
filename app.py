import streamlit as st

# 1. Initialize Session
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['role'] = None

# 2. Login Page
def login_page():
    st.title("🔒 Institutional VIP Node")
    key = st.text_input("Enter Node Key", type="password")
    if st.button("Initialize Node"):
        if key == "ADMIN_PASS": # Aapka Admin Password
            st.session_state['authenticated'] = True
            st.session_state['role'] = 'admin'
            st.rerun()
        elif key == "USER_PASS": # Aapka User Password
            st.session_state['authenticated'] = True
            st.session_state['role'] = 'user'
            st.rerun()
        else:
            st.error("Invalid Node Key")

# 3. Main Logic (Admin & User Control)
if not st.session_state['authenticated']:
    login_page()
else:
    if st.session_state['role'] == 'admin':
        # Yahan ADMIN PANEL ka pura code aayega
        st.subheader("Admin Control Panel")
        # ... (Manage users, settings, etc.)
    elif st.session_state['role'] == 'user':
        # Yahan USER PANEL ka pura code aayega
        st.subheader("User Analytics Desk")
        # ... (Dashboard, Signals, etc.)
    
    if st.sidebar.button("Logout"):
        st.session_state['authenticated'] = False
        st.rerun()
