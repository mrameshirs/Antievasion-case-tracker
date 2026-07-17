# ui_visualize.py
import streamlit as st
import pandas as pd
import plotly.express as px

from config import CASES_DATA_PATH
from dropbox_utils import read_from_spreadsheet


def visualize_dashboard(dbx):
    st.title("📊 Case Visualizations")

    df = read_from_spreadsheet(dbx, CASES_DATA_PATH)
    if df.empty:
        st.info("No cases have been uploaded yet.")
        return

    df["Date_of_Approval"] = pd.to_datetime(df["Date_of_Approval"], errors="coerce")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Cases", len(df))
    col2.metric("Groups Involved", df["Investigation_Group"].nunique())
    col3.metric("Categories", df["Category"].nunique())
    if "Status" in df.columns:
        open_statuses = [s for s in df["Status"].unique() if s != "Closed"]
        col4.metric("Open Cases", df["Status"].isin(open_statuses).sum())

    st.markdown("---")

    # --- Date-wise case counts ---
    st.subheader("Date-wise Number of Cases")
    granularity = st.radio("Group by", options=["Day", "Month"], horizontal=True, index=1)
    if not df["Date_of_Approval"].isna().all():
        if granularity == "Day":
            date_counts = df.groupby(df["Date_of_Approval"].dt.date).size().reset_index(name="Count")
            date_counts.columns = ["Date", "Count"]
            fig1 = px.bar(date_counts, x="Date", y="Count", text="Count")
        else:
            date_counts = df.groupby(df["Date_of_Approval"].dt.to_period("M")).size().reset_index(name="Count")
            date_counts["Date_of_Approval"] = date_counts["Date_of_Approval"].astype(str)
            fig1 = px.bar(date_counts, x="Date_of_Approval", y="Count", text="Count",
                          labels={"Date_of_Approval": "Month"})
        fig1.update_traces(textposition="outside")
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("No valid approval dates to chart yet.")

    # --- Group-wise case counts ---
    st.subheader("Group-wise Assigned Cases")
    group_counts = df["Investigation_Group"].value_counts().reset_index()
    group_counts.columns = ["Investigation_Group", "Count"]
    fig2 = px.bar(group_counts, x="Investigation_Group", y="Count", text="Count", color="Investigation_Group")
    fig2.update_traces(textposition="outside")
    st.plotly_chart(fig2, use_container_width=True)

    # --- Category-wise breakdown ---
    st.subheader("Category-wise Breakdown")
    cat_counts = df["Category"].value_counts().reset_index()
    cat_counts.columns = ["Category", "Count"]
    c1, c2 = st.columns(2)
    with c1:
        fig3 = px.pie(cat_counts, names="Category", values="Count", hole=0.4)
        st.plotly_chart(fig3, use_container_width=True)
    with c2:
        fig4 = px.bar(cat_counts, x="Category", y="Count", text="Count", color="Category")
        fig4.update_traces(textposition="outside")
        st.plotly_chart(fig4, use_container_width=True)

    # --- Status-wise breakdown ---
    if "Status" in df.columns:
        st.subheader("Status-wise Breakdown")
        status_counts = df["Status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        fig5 = px.bar(status_counts, x="Status", y="Count", text="Count", color="Status")
        fig5.update_traces(textposition="outside")
        st.plotly_chart(fig5, use_container_width=True)
