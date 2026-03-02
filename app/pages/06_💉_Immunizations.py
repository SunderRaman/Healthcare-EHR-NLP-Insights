import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from utils.data_access import get_filtered_data
from components.filters import render_global_filters

from utils.immunization_utils import (
    preprocess_immunizations,
    immunization_time_series,
    vaccine_rank,
    age_group_coverage,
    vaccine_age_heatmap,
    fig_top_vaccines,
    fig_time_series,
    fig_age_coverage,
    fig_heatmap,
    generate_immunization_insights
)


# ---------------------------------------------------------
# MAIN PAGE
# ---------------------------------------------------------
def main():
    st.title("💉 Immunizations Dashboard")

    # Global sidebar filters (read-only mode)
    render_global_filters(
        st.session_state.patients,
        st.session_state.encounters,
        read_only=True
    )

    # Fetch filtered data
    (
        patients,
        encounters,
        conditions,
        medications,
        procedures,
        immunizations,
        observations,
    ) = get_filtered_data()

    if immunizations.empty:
        st.warning("No immunization data available for the selected filters.")
        return

    # Preprocess + enrich data
    df = preprocess_immunizations(immunizations, patients)
   
    # -------------------------------------------------
    # KPIs
    # -------------------------------------------------
    st.subheader("📊 Key Metrics")

    total = len(df)
    unique_pts = df["PATIENT"].nunique()
    avg_vax = round(total / unique_pts, 2)
    total_cost = df["BASE_COST"].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Immunizations", total)
    c2.metric("Unique Patients Vaccinated", unique_pts)
    c3.metric("Avg Vaccines per Patient", avg_vax)
    c4.metric("Total Vaccine Cost", f"${total_cost:,.2f}")

    st.markdown("---")

    # -------------------------------------------------
    # CHART 1 — Most Common Vaccines
    # -------------------------------------------------
    st.subheader("Top Vaccines Administered")
    top_vax = vaccine_rank(df)
     # Truncate description for x-axis, but keep full text for hover
    top_vax["short_desc"] = top_vax["DESCRIPTION"].apply(
            lambda x: x if len(x) <= 20 else x[:20] + "..."
    )
    fig_top = px.bar(
        top_vax,
        x="short_desc",
        y="count",
        custom_data=["DESCRIPTION"],  # full name shown on hover
        title="Most Common Vaccines"
    )
    # Force hover to show full DESCRIPTION
    fig_top.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><extra></extra>"
    )

    fig_top.update_layout(
        xaxis_title="Vaccine",
        yaxis_title="Count",
        xaxis_tickangle=-45
    )
    st.plotly_chart(fig_top, width='stretch')
    
    # -------------------------------------------------
    # CHART 2 — Time Series
    # -------------------------------------------------
    st.subheader("Vaccination Trend Over Time")
    ts = immunization_time_series(df)
    st.plotly_chart(fig_time_series(ts), width='stretch')

    # Calculate seasonality
    seasonality = df.copy()
    seasonality["month"] = pd.to_datetime(seasonality["DATE"]).dt.month
    seasonality = (
        seasonality.groupby("month")
        .size()
        .reset_index(name="count")
)

    # -------------------------------------------------
    # CHART 3 — Age Group Coverage
    # -------------------------------------------------
    st.subheader("Coverage by Age Group")
    cov = age_group_coverage(df, patients)
    # print(f"columns in cov is {cov.columns.tolist()}")
    cov["pct"] = (cov["vaccinated"] / cov["cohort"]) * 100
    st.plotly_chart(fig_age_coverage(cov), width='stretch')

    # create by_age for AI insights with a 'count' column
    by_age = (
      df.groupby("age_band")["PATIENT"]
      .nunique()
      .reset_index(name="count")
    )
    # -------------------------------------------------
    # CHART 4 — Vaccine × Age Heatmap
    # -------------------------------------------------
    st.subheader("Vaccine Usage Heatmap Across Age Groups")
    pivot = vaccine_age_heatmap(df)
    st.plotly_chart(fig_heatmap(pivot), width='stretch')

    st.markdown("---")

    # -------------------------------------------------
    # DOWNLOAD CLEAN DATASET
    # -------------------------------------------------
    st.subheader("Download Cleaned Immunization Dataset")
    st.download_button(
        "Download CSV",
        df.to_csv(index=False),
        "clean_immunizations.csv",
        mime="text/csv"
    )

    # --------- AI Insights-----------
    st.markdown("## 🤖 AI Insights")

    insights = generate_immunization_insights(df, top_vax, by_age, seasonality)

    for ins in insights:
        if ins["severity"] == "high":
            st.warning("• " + ins["message"])
        elif ins["severity"] == "medium":
            st.info("• " + ins["message"])
        else:
            st.caption("• " + ins["message"])

    st.session_state.immunization_insights = insights

if __name__ == "__main__":
    main()
