import streamlit as st

# Session initialize
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['role'] = None

# Login Logic
if not st.session_state['authenticated']:
    st.title("🔒 Institutional VIP Node")
    with st.form("login_form"):
        key = st.text_input("Enter Node Key", type="password")
        submit = st.form_submit_button("Initialize Node")
    
    if submit:
        if key == "manishadmin":
            st.session_state['authenticated'] = True
            st.session_state['role'] = 'admin'
            st.rerun()
        elif key == "goldmaster77":
            st.session_state['authenticated'] = True
            st.session_state['role'] = 'user'
            st.rerun()
        else:
            st.error("Invalid Node Key")
else:
    # Authenticated State
    if st.session_state['role'] == 'admin':
        st.subheader("Admin Control Panel")
        # Admin access here
    else:
        st.subheader("User Analytics Desk")
        # User access here

    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()
