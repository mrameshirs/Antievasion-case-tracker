# ui_login.py
import streamlit as st
from config import USER_CREDENTIALS, USER_ROLES


def login_page():
    st.title("🔍 GST Anti-Evasion Case Tracker")
    st.subheader("Mumbai East Commissionerate")
    st.markdown("---")

    with st.form("login_form"):
        username = st.text_input("Username").strip().lower()
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = USER_ROLES[username]
                st.rerun()
            else:
                st.error("Invalid username or password.")
