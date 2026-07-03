import streamlit as st

# --- LOGIN PAGE FUNCTION ---
def show_login():
    st.title("🔒 Institutional VIP Node")
    with st.form("login_form"):
        key = st.text_input("Enter Node Key", type="password")
        submit = st.form_submit_button("Initialize Node")
    
    if submit:
        # Aapka purana password logic
        if key == "ADMIN123": 
            st.session_state['authenticated'] = True
            st.session_state['role'] = 'admin'
            st.rerun()
        elif key == "USER123":
            st.session_state['authenticated'] = True
            st.session_state['role'] = 'user'
            st.rerun()
        else:
            st.error("Invalid Node Key")

# --- MAIN LOGIC ---
def main():
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
        st.session_state['role'] = None

    if not st.session_state['authenticated']:
        show_login() # Ab ye function yahan defined hai
    else:
        # Logged in state
        st.sidebar.success(f"Logged in as {st.session_state['role']}")
        if st.sidebar.button("Logout"):
            st.session_state.clear()
            st.rerun()
        
        # Dashboard logic
        if st.session_state['role'] == 'admin':
            st.subheader("Admin Control Panel")
        else:
            st.subheader("User Analytics Desk")

if __name__ == '__main__':
    main()
