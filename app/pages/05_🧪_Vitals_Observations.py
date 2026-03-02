# pages/Vitals_Observations.py
import streamlit as st
import plotly.express as px
import pandas as pd
import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)


from utils.vitals import (
    clean_vitals,
    get_latest_vitals_cached,
    compute_bmi_cached,
    compute_clinical_flags,
    vitals_trend_cached,
    patient_vitals_timeline_cached,
    get_abnormal_vitals_summary,
    compute_news2_score,
    get_age_band
)

from utils.vitals_news2 import (
    compute_news2_scores,
    compute_vitals_correlation,
    plot_news2_timeseries,
    plot_news2_distribution
)

from utils.data_access import get_filtered_data  # assuming you have this

st.set_page_config(page_title="Vitals & Observations", layout="wide")

def main():
    st.title("🩺 Vitals & Observations")

    # Load filtered data from shared pipeline (get_filtered_data returns observations)
    patients, encounters, conditions, medications, procedures, immunizations, observations = get_filtered_data()

    if observations is None or observations.empty:
        st.warning("No observations data available for the current filters.")
        return

    # Clean and normalize vitals (cached)
    with st.spinner("Cleaning vitals data..."):
        vitals_tidy = clean_vitals(observations)

    st.info(f"Vitals rows after mapping: {len(vitals_tidy)}")

    # Latest vitals per patient
    latest = get_latest_vitals_cached(vitals_tidy)

    # BMI
    bmi_df = compute_bmi_cached(latest)

    # Clinical flags
    flags = compute_clinical_flags(latest, bmi_df)

    # NEWS2
    news2 = compute_news2_score(latest)

    # KPI row
    c1, c2, c3, c4, c5 = st.columns(5)
    total_patients = patients["id"].nunique()
    pct_hypertension = flags["hypertension"].mean() * 100 if not flags.empty else 0
    pct_tachy = flags["tachycardia"].mean() * 100 if not flags.empty else 0
    pct_fever = flags["fever"].mean() * 100 if not flags.empty else 0
    pct_hypoxia = flags["hypoxia"].mean() * 100 if not flags.empty else 0

    c1.metric("Cohort patients", f"{total_patients}")
    c2.metric("Hypertension (%)", f"{pct_hypertension:.1f}%")
    c3.metric("Tachycardia (%)", f"{pct_tachy:.1f}%")
    c4.metric("Fever (%)", f"{pct_fever:.1f}%")
    c5.metric("Hypoxia (%)", f"{pct_hypoxia:.1f}%")

    # Distribution charts
    st.subheader("Vital Distributions (latest per patient)")
    # prepare pivot for distributions
    pivot = latest.copy()
    # choose vitals to plot
    vitals_to_plot = ["sbp", "dbp", "hr", "rr", "temp_c", "spo2", "weight_kg", "height_cm"]
    for v in vitals_to_plot:
        if v not in pivot.columns:
            pivot[v] = None

    col1, col2 = st.columns(2)
    with col1:
        fig_sbp = px.histogram(pivot, x="sbp", nbins=50, title="Systolic BP (latest)")
        st.plotly_chart(fig_sbp, use_container_width=True)
        fig_hr = px.histogram(pivot, x="hr", nbins=50, title="Heart Rate (latest)")
        st.plotly_chart(fig_hr, use_container_width=True)
    with col2:
        fig_temp = px.histogram(pivot, x="temp_c", nbins=50, title="Temperature (°C)")
        st.plotly_chart(fig_temp, use_container_width=True)
        fig_spo2 = px.histogram(pivot, x="spo2", nbins=50, title="SpO2 (%)")
        st.plotly_chart(fig_spo2, use_container_width=True)

    # Time series (cohort) example: heart rate trend
    st.subheader("Cohort Trends")
    hr_trend = vitals_trend_cached(vitals_tidy, "hr", freq="W")
    if not hr_trend.empty:
        fig_trend = px.line(hr_trend, x="DATE", y="median", title="Median Heart Rate (weekly)")
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Not enough HR data for cohort trend.")

    # Age-band breakdown of abnormal flags
    st.subheader("Abnormal Flags by Age Group")
    if not flags.empty:
        flags = flags.merge(patients[["id", "age"]].rename(columns={"id": "PATIENT"}), on="PATIENT", how="left")
        flags["age_band"] = flags["age"].apply(get_age_band)
        ab_counts = flags.groupby("age_band")[["tachycardia", "hypertension", "fever", "hypoxia"]].mean().reset_index()
        ab_melt = ab_counts.melt(id_vars="age_band", var_name="flag", value_name="pct")
        fig_flags = px.bar(ab_melt, x="age_band", y="pct", color="flag", barmode="group",
                           labels={"pct":"Fraction with flag"})
        st.plotly_chart(fig_flags, use_container_width=True)

    # Patient-level drilldown
    st.subheader("Patient Vitals Timeline")
    patient_ids = sorted(vitals_tidy["PATIENT"].unique().tolist())
    sel = st.selectbox("Select patient", options=patient_ids, index=0)
    timeline = patient_vitals_timeline_cached(vitals_tidy, sel)
    if not timeline.empty:
        # example chart: HR over time
        hr_df = timeline[timeline["vital"] == "hr"]
        if not hr_df.empty:
            fig_p = px.line(hr_df, x="DATE", y="value", title=f"Heart Rate timeline for {sel}")
            st.plotly_chart(fig_p, use_container_width=True)
        st.dataframe(timeline.head(200), use_container_width=True)
    else:
        st.info("No vitals for this patient.")

    # NEWS2 distribution
    if not news2.empty:
        st.subheader("NEWS2 Score Distribution (latest)")
        fig_news = px.histogram(news2, x="news2", nbins=10, title="NEWS2 Score")
        st.plotly_chart(fig_news, use_container_width=True)

    # Download cleaned vitals
    st.markdown("---")
    st.download_button("Download cleaned vitals (CSV)", vitals_tidy.to_csv(index=False), "vitals_cleaned.csv", mime="text/csv")
    # Converting the dataframe to wide format
    clean_df_wide = (vitals_tidy.pivot_table(
            index=["PATIENT", "DATE"],
            columns="vital",
            values="value",
            aggfunc="mean"
    ).reset_index()
)
    print(f"Columns in clean_df_wide: {clean_df_wide.columns.tolist()}")
    # NEWS2 scores detailed section
    st.subheader("NEWS2 Early Warning Score")
    clean_news = compute_news2_scores(clean_df_wide)
    st.success("NEWS2 scores computed successfully.")
    
    # NEWS2 correlation heatmap
    st.markdown("### NEWS2 Score Distribution (Cohort)")
    fig_news_dist = plot_news2_distribution(clean_news)
    st.plotly_chart(fig_news_dist, use_container_width=True)
    
    # Correlation heatmap
    st.markdown("### Correlation Heatmap of Vitals & Lab Values")
    fig_corr = compute_vitals_correlation(clean_df_wide)
    st.plotly_chart(fig_corr, use_container_width=True)

    # Pick patients with ≥1 NEWS2 value
    eligible_patients = (
        clean_news.groupby("PATIENT")["NEWS2"]
        .count()
        .reset_index(name="n")
    )
    eligible_patients = eligible_patients[eligible_patients["n"] >= 1]["PATIENT"].tolist()
    selected = st.selectbox("Select patient for NEWS2 trend:", eligible_patients)
    fig_ts = plot_news2_timeseries(clean_news, selected)
    if fig_ts:
        st.plotly_chart(fig_ts, use_container_width=True)
    else:
        st.info("This patient does not have ≥ 3 distinct observation dates (Option B).")

if __name__ == "__main__":
    main()
