# app.py
import streamlit as st
from streamlit_option_menu import option_menu
from io import BytesIO
import pandas as pd

from config import (
    DROPBOX_ROOT_PATH, CASE_PHOTOS_PATH, CASES_DATA_PATH, DATA_SHEET_COLUMNS
)
from dropbox_utils import get_dropbox_client, create_folder, upload_file, log_activity
from ui_login import login_page
from ui_upload import upload_case_dashboard
from ui_view_search import view_search_dashboard
from ui_visualize import visualize_dashboard
from ui_edit import edit_case_dashboard

st.set_page_config(page_title="GST Anti-Evasion Case Tracker", page_icon="🔍", layout="wide")


def initialize_session_state():
    states = {
        'logged_in': False,
        'username': "",
        'role': "",
        'dbx': None,
        'dropbox_initialized': False,
        'activity_logged': False,
    }
    for key, value in states.items():
        if key not in st.session_state:
            st.session_state[key] = value


def initialize_dropbox_structure(dbx):
    create_folder(dbx, DROPBOX_ROOT_PATH)
    create_folder(dbx, CASE_PHOTOS_PATH)
    try:
        dbx.files_get_metadata(CASES_DATA_PATH)
    except Exception:
        output = BytesIO()
        pd.DataFrame(columns=DATA_SHEET_COLUMNS).to_excel(output, index=False, engine='xlsxwriter')
        upload_file(dbx, output.getvalue(), CASES_DATA_PATH)


def main():
    initialize_session_state()

    if not st.session_state.logged_in:
        login_page()
        return

    if not st.session_state.dbx:
        with st.spinner("Connecting to Dropbox..."):
            st.session_state.dbx = get_dropbox_client()
            if st.session_state.dbx:
                st.rerun()
        return

    if not st.session_state.dropbox_initialized:
        with st.spinner("Initializing app data structure..."):
            initialize_dropbox_structure(st.session_state.dbx)
            st.session_state.dropbox_initialized = True
            st.rerun()
        return

    if not st.session_state.activity_logged:
        log_activity(st.session_state.dbx, st.session_state.username, st.session_state.role)
        st.session_state.activity_logged = True

    dbx = st.session_state.dbx
    role = st.session_state.role

    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.caption(f"Role: {role}")

        if role == "Admin":
            menu_options = ["Upload Case", "View & Search", "Visualizations", "Edit Cases"]
            menu_icons = ["cloud-upload", "search", "bar-chart", "pencil-square"]
        else:  # Viewer
            menu_options = ["View & Search", "Visualizations"]
            menu_icons = ["search", "bar-chart"]

        selected = option_menu(
            menu_title="Navigation",
            options=menu_options,
            icons=menu_icons,
            default_index=0,
        )

        st.markdown("---")
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    if selected == "Upload Case" and role == "Admin":
        upload_case_dashboard(dbx)
    elif selected == "View & Search":
        view_search_dashboard(dbx)
    elif selected == "Visualizations":
        visualize_dashboard(dbx)
    elif selected == "Edit Cases" and role == "Admin":
        edit_case_dashboard(dbx)
    else:
        st.error("You do not have access to this section.")


if __name__ == "__main__":
    main()
