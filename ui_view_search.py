# ui_view_search.py
import streamlit as st
import pandas as pd

from config import CASES_DATA_PATH, INVESTIGATION_GROUPS, CASE_CATEGORIES, STATUS_OPTIONS
from dropbox_utils import read_from_spreadsheet, download_file


def _load_cases_df(dbx):
    df = read_from_spreadsheet(dbx, CASES_DATA_PATH)
    if not df.empty and "Date_of_Approval" in df.columns:
        df["Date_of_Approval"] = pd.to_datetime(df["Date_of_Approval"], errors="coerce")
    return df


def view_search_dashboard(dbx):
    st.title("🔎 View & Search Cases")

    df = _load_cases_df(dbx)
    if df.empty:
        st.info("No cases have been uploaded yet.")
        return

    with st.expander("Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            search_text = st.text_input("Search (GSTIN / Trade Name / Summary)")
        with col2:
            group_filter = st.multiselect("Investigation Group", options=INVESTIGATION_GROUPS)
        with col3:
            category_filter = st.multiselect("Category", options=CASE_CATEGORIES)

        col4, col5 = st.columns(2)
        with col4:
            status_filter = st.multiselect("Status", options=STATUS_OPTIONS)
        with col5:
            date_range = st.date_input("Date of Approval range", value=())

    filtered_df = df.copy()

    if search_text:
        mask = (
            filtered_df["GSTINs"].astype(str).str.contains(search_text, case=False, na=False)
            | filtered_df["Trade_Names"].astype(str).str.contains(search_text, case=False, na=False)
            | filtered_df["Case_Summary"].astype(str).str.contains(search_text, case=False, na=False)
        )
        filtered_df = filtered_df[mask]

    if group_filter:
        filtered_df = filtered_df[filtered_df["Investigation_Group"].isin(group_filter)]
    if category_filter:
        filtered_df = filtered_df[filtered_df["Category"].isin(category_filter)]
    if status_filter:
        filtered_df = filtered_df[filtered_df["Status"].isin(status_filter)]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        filtered_df = filtered_df[
            (filtered_df["Date_of_Approval"] >= pd.Timestamp(start))
            & (filtered_df["Date_of_Approval"] <= pd.Timestamp(end))
        ]

    st.markdown(f"**{len(filtered_df)}** case(s) found")

    # Show the table with a "Photos" indicator column (actual viewing happens below).
    display_df = filtered_df.copy()
    display_df["Photos"] = display_df["Photo_Links"].apply(
        lambda x: f"📷 {len([p for p in str(x).split(';') if p.strip()])}" if str(x).strip() else "—"
    )
    table_cols = [c for c in display_df.columns if c != "Photo_Links"]
    st.dataframe(display_df[table_cols], use_container_width=True, hide_index=True)

    csv = filtered_df.drop(columns=["Photo_Links"], errors="ignore").to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download filtered data as CSV", data=csv, file_name="anti_evasion_cases.csv", mime="text/csv")

    st.markdown("---")
    st.markdown("### 📷 View Case Photos")
    if not filtered_df.empty:
        serial_options = filtered_df["Serial_No"].dropna().astype(int).tolist()
        selected_serial = st.selectbox("Select a Serial No. to view its uploaded photos", options=serial_options)
        row = filtered_df[filtered_df["Serial_No"] == selected_serial].iloc[0]

        if st.button("🖼️ Show Photos for this Case", type="primary"):
            links = [l.strip() for l in str(row.get("Photo_Links", "")).split(";") if l.strip()]
            if not links:
                st.info("No photos were uploaded for this case.")
            else:
                with st.spinner("Fetching photos from Dropbox..."):
                    photo_cols = st.columns(min(len(links), 3))
                    for i, path in enumerate(links):
                        content = download_file(dbx, path)
                        with photo_cols[i % 3]:
                            if content:
                                st.image(content, caption=path.split("/")[-1], use_container_width=True)
                            else:
                                st.warning(f"Could not load: {path}")
