import streamlit as st

# 1. State initialize
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['role'] = None

# 2. Login Page
def login_page():
    st.title("🔒 Institutional VIP Node")
    # Form ka istemal zaroori hai taaki 'Enter' dabane par bhi kaam kare
    with st.form("login_form"):
        key = st.text_input("Enter Node Key", type="password")
        submit = st.form_submit_button("Initialize Node")
    
    if submit:
        if key == "YOUR_ADMIN_PASSWORD": 
            st.session_state['authenticated'] = True
            st.session_state['role'] = 'admin'
            st.rerun() # Refresh karke dashboard par le jayega
        elif key == "YOUR_USER_PASSWORD":
            st.session_state['authenticated'] = True
            st.session_state['role'] = 'user'
            st.rerun()
        else:
            st.error("Invalid Node Key")

# 3. Main Switcher
if st.session_state['authenticated']:
    if st.session_state['role'] == 'admin':
        st.subheader("Admin Control Panel")
        # Admin ke liye agents dikhao...
    else:
        st.subheader("User Analytics Desk")
        # User ke liye sirf dashboard...
    
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()
else:
    login_page()
