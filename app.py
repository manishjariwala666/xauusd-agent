import streamlit as st

# Role-based redirection logic
def main():
    if 'user_role' not in st.session_state:
        st.session_state.role = None
        
    if st.session_state.role == 'admin':
        import admin_panel
        admin_panel.show()
    elif st.session_state.role == 'user':
        import user_portal
        user_portal.show()
    else:
        # Show Login Page with Verification Logic
        show_login()

main()
