import streamlit as st

# 1. Initialize State
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['role'] = None

# 2. Login Page (WITH FORM FIX)
if not st.session_state['authenticated']:
    st.title("🔒 Institutional VIP Node")
    with st.form("login_form"): # Form se reset issue solve ho jayega
        key = st.text_input("Enter Node Key", type="password")
        submit = st.form_submit_button("Initialize Node")
    
    if submit:
        if key == "YOUR_ADMIN_PASSWORD": # Apna password yahan rakhein
            st.session_state['authenticated'] = True
            st.session_state['role'] = 'admin'
            st.rerun()
        elif key == "YOUR_USER_PASSWORD":
            st.session_state['authenticated'] = True
            st.session_state['role'] = 'user'
            st.rerun()
        else:
            st.error("Invalid Node Key")
else:
    # 3. Main Content
    if st.session_state['role'] == 'admin':
        st.subheader("Admin Control Panel")
        # Admin features
    else:
        st.subheader("User Analytics Desk")
        # Dashboard features
        
    if st.sidebar.button("Logout"):
        st.session_state['authenticated'] = False
        st.rerun()
