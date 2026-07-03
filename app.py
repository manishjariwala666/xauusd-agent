import streamlit as st

# 1. Page Config (Sabse upar)
st.set_page_config(page_title="Institutional Node", layout="wide")

# 2. Session Initialization
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['role'] = None

# 3. Logic: Agar logged in nahi hain toh Login Page dikhao
if not st.session_state['authenticated']:
    st.title("🔒 Institutional VIP Node")
    key = st.text_input("Enter Node Key", type="password")
    if st.button("Initialize Node"):
        # Yahan apna purana password aur role logic daalein
        if key == "YOUR_ADMIN_PASS":
            st.session_state['authenticated'] = True
            st.session_state['role'] = 'admin'
            st.rerun()
        elif key == "YOUR_USER_PASS":
            st.session_state['authenticated'] = True
            st.session_state['role'] = 'user'
            st.rerun()
        else:
            st.error("Invalid Node Key")
            
else:
    # 4. Yahan aapka Admin/User panel ka logic hai
    if st.session_state['role'] == 'admin':
        st.subheader("Admin Control Panel")
        # Yahan Admin ke features daalein
    elif st.session_state['role'] == 'user':
        st.subheader("User Analytics Desk")
        # Yahan User ke features (dashboard) daalein
    
    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state['authenticated'] = False
        st.session_state['role'] = None
        st.rerun()
