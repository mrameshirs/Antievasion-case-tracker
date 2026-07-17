# ui_edit.py
from datetime import datetime

import streamlit as st
import pandas as pd

from config import CASES_DATA_PATH, INVESTIGATION_GROUPS, CASE_CATEGORIES, STATUS_OPTIONS
from dropbox_utils import read_from_spreadsheet, update_case_row
from validators import validate_gstins, validate_investigation_group


def edit_case_dashboard(dbx):
    st.title("✏️ Edit Data Sheet")
    st.caption("Correct any errors identified in previously uploaded cases.")

    df = read_from_spreadsheet(dbx, CASES_DATA_PATH)
    if df.empty:
        st.info("No cases have been uploaded yet.")
        return

    serial_options = df["Serial_No"].dropna().astype(int).tolist()
    selected_serial = st.selectbox("Select Case (Serial No.)", options=serial_options)

    row = df[df["Serial_No"] == selected_serial].iloc[0]

    with st.form("edit_case_form"):
        gstins_raw = st.text_input(
            "GSTIN(s) — separate multiple with a comma or semicolon",
            value=str(row.get("GSTINs", "") or "")
        )
        trade_names_raw = st.text_input(
            "Trade Name(s) — same order as GSTINs above, comma/semicolon separated",
            value=str(row.get("Trade_Names", "") or "")
        )
        case_summary = st.text_area("Case Summary", value=str(row.get("Case_Summary", "") or ""), height=120)

        cat_val = row.get("Category")
        cat_index = CASE_CATEGORIES.index(cat_val) if cat_val in CASE_CATEGORIES else 0
        category = st.selectbox("Category", options=CASE_CATEGORIES, index=cat_index)

        col1, col2 = st.columns(2)
        with col1:
            grp_val = row.get("Investigation_Group")
            grp_index = INVESTIGATION_GROUPS.index(grp_val) if grp_val in INVESTIGATION_GROUPS else 0
            investigation_group = st.selectbox("Investigation Group (A–I only)", options=INVESTIGATION_GROUPS, index=grp_index)
        with col2:
            status_val = row.get("Status")
            status_index = STATUS_OPTIONS.index(status_val) if status_val in STATUS_OPTIONS else 0
            status = st.selectbox("Status of Investigation", options=STATUS_OPTIONS, index=status_index)

        try:
            default_date = pd.to_datetime(row.get("Date_of_Approval")).date()
        except Exception:
            default_date = datetime.today().date()
        date_of_approval = st.date_input("Date of Approval by Principal Commissioner", value=default_date)

        st.text_input("Photo Links (read-only)", value=str(row.get("Photo_Links", "") or ""), disabled=True)

        submitted = st.form_submit_button("💾 Save Changes", type="primary")

        if submitted:
            valid_gstins, invalid_gstins = validate_gstins(gstins_raw)
            trade_names_list = [t.strip() for t in trade_names_raw.replace(";", ",").split(",") if t.strip()]

            errors = []
            if invalid_gstins:
                errors.append(
                    "The following GSTIN(s) don't match the required 15-character format and must be "
                    f"corrected before saving: {', '.join(invalid_gstins)}"
                )
            if not valid_gstins:
                errors.append("At least one valid GSTIN is required.")
            if not trade_names_list:
                errors.append("At least one Trade Name is required.")
            if not validate_investigation_group(investigation_group):
                errors.append("Investigation Group must be one of A–I.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                updated_fields = {
                    "GSTINs": "; ".join(valid_gstins),
                    "Trade_Names": "; ".join(trade_names_list),
                    "Case_Summary": case_summary.strip(),
                    "Category": category,
                    "Investigation_Group": investigation_group,
                    "Status": status,
                    "Date_of_Approval": date_of_approval.strftime("%Y-%m-%d"),
                }
                with st.spinner("Saving changes..."):
                    if update_case_row(dbx, CASES_DATA_PATH, selected_serial, updated_fields):
                        st.success(f"Case #{selected_serial} updated successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to update the case. Please try again.")
