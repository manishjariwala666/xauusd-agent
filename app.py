import streamlit as st

# State initialization
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['role'] = None

# Login Page
def login():
    st.title("🔒 Institutional VIP Node")
    # Form ka use krke hum state ko persist karenge
    with st.form("login"):
        key = st.text_input("Enter Node Key", type="password")
        submit = st.form_submit_button("Initialize Node")
        
        if submit:
            if key == "manishadmin":
                st.session_state.authenticated = True
                st.session_state.role = "admin"
                st.rerun()
            elif key == "goldmaster77":
                st.session_state.authenticated = True
                st.session_state.role = "user"
                st.rerun()
            else:
                st.error("Invalid Node Key")

# Dashboard Logic
def dashboard():
    if st.session_state.role == "admin":
        st.subheader("Admin Control Panel")
        # Admin ke features yahan
    else:
        st.subheader("User Analytics Desk")
        # User ke features yahan
    
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

# Logic flow
if st.session_state.authenticated:
    dashboard()
else:
    login()
