import streamlit as st

# ========= PAGE CONFIG ========= #

st.set_page_config(
    page_title="AI Market Analytics Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========= IMPORTS ========= #

try:
    from config import APP_NAME
    from core.auth import (
        initialize_session,
        is_authenticated,
        logout_user,
        get_current_role,
    )

    from pages.login import login_page

    from admin.dashboard import admin_dashboard
    from user.dashboard import user_dashboard

except Exception as e:
    st.error("Project initialization failed.")
    st.exception(e)
    st.stop()

# ========= SESSION ========= #

initialize_session()

# ========= SIDEBAR ========= #

with st.sidebar:

    st.title(APP_NAME)

    st.divider()

    if is_authenticated():

        st.success("Logged In")

        st.write(f"Role : **{get_current_role().upper()}**")

        st.divider()

        if st.button("Logout", use_container_width=True):
            logout_user()
            st.rerun()

# ========= ROUTER ========= #

if not is_authenticated():

    login_page()

else:

    role = get_current_role()

    if role == "admin":

        admin_dashboard()

    elif role == "user":

        user_dashboard()

    else:

        st.error("Invalid User Role")

        logout_user()

        st.rerun()

# ========= FOOTER ========= #

st.divider()

st.caption("© 2026 AI Market Analytics Pro")
