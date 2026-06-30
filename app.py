# --- LOGIN SCREEN ---
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔒 VIP AI Terminal</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Algorithmic Signal Network</p>", unsafe_allow_html=True)
    
    # 3 Columns banayein aur center wali col2 ko use karein width control karne ke liye
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["🔑 Sign In", "📝 Register"])
        
        with tab1:
            user_input = st.text_input("Email or Username")
            pass_input = st.text_input("Password", type="password")
            if st.button("Log In", use_container_width=True):
                if user_input == "manishadmin" and pass_input == "goldmaster77":
                    st.session_state.logged_in = True
                    st.session_state.role = "ADMIN"
                    st.session_state.username = "Manissh (Admin)"
                    st.rerun()
                else:
                    try:
                        res = supabase.table("users").select("*").eq("username", user_input).eq("password", pass_input).execute()
                        if len(res.data) > 0:
                            st.session_state.logged_in = True
                            st.session_state.role = "USER"
                            st.session_state.username = res.data[0]["username"]
                            st.rerun()
                        else:
                            st.error("Invalid Credentials")
                    except Exception as e:
                        st.error("Database Connection Error")
                        
        with tab2:
            reg_user = st.text_input("Create Username")
            reg_pass = st.text_input("Create Password", type="password")
            reg_phone = st.text_input("WhatsApp / Telegram Number")
            if st.button("Register & Activate Alerts", use_container_width=True):
                if reg_user and reg_pass and reg_phone:
                    try:
                        supabase.table("users").insert({
                            "username": reg_user, 
                            "password": reg_pass, 
                            "phone": reg_phone,
                            "role": "USER"
                        }).execute()
                        st.success("Registration Successful! Please Sign In.")
                    except Exception as e:
                        st.error("Username already exists.")
                else:
                    st.warning("Please fill all details.")
