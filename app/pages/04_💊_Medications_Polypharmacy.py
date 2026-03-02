import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os
from utils.medication_analytics import generate_medication_insights

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)


from utils.data_access import get_filtered_data
from components.filters import render_global_filters  # noqa: E402

from utils.polypharmacy import (
    compute_daily_polypharmacy_cached,
    enrich_poly_summary_cached,
    get_poly_days_cached,
    get_top_meds_cached,
    get_age_band,
    get_age_band_breakdown,
    categorize_duration,
    get_chronic_vs_acute_counts,
    get_duration_categories,
    get_patient_timeline,
    compute_med_cooccurrence_cached,
    get_poly_by_class
)

from utils.med_class_map import load_med_class_map


def main():
    st.title("💊 Medications & Polypharmacy")

    # --- Global filters (read-only) ---
    render_global_filters(
        st.session_state.patients,
        st.session_state.encounters,
        read_only=True,
    )

    # --- Filtered data ---
    (
        patients,
        encounters,
        conditions,
        medications,
        procedures,
        immunizations,
        observations,
    ) = get_filtered_data()

    if medications.empty:
        st.warning("No medication records available for these filters.")
        return

    med_class_map = load_med_class_map()

    # --- Sidebar threshold ---
    with st.sidebar:
        st.markdown("---")
        poly_threshold = st.slider(
            "Polypharmacy threshold (concurrent meds ≥)",
            min_value=2, max_value=10, value=5, step=1
        )

    # --- Compute polypharmacy (cached) ---
    with st.status("Computing polypharmacy metrics...") as status:

        status.update(label="Step 1: Daily polypharmacy calculation", state="running")
        daily_counts, poly_summary = compute_daily_polypharmacy_cached(
            medications, threshold=poly_threshold
        )
        status.update(label="Step 2: Age & duration stats", state="running")
        poly_summary = enrich_poly_summary_cached(poly_summary, patients)

        # Categorize
        poly_summary["age_band"] = poly_summary["age"].apply(get_age_band)
        poly_summary["duration_category"] = poly_summary["poly_days"].apply(categorize_duration)

        status.update(label="Step 3: Polypharmacy day extraction", state="running")
        poly_days = get_poly_days_cached(daily_counts, poly_threshold)

        status.update(label="Step 4: Top medication extraction", state="running")
        top_meds = get_top_meds_cached(medications, poly_days)

        status.update(label="Step 5: Age Bank Breakdown extraction", state="running")
        age_fig = get_age_band_breakdown(poly_summary, patients)

        status.update(label="Step 6: Chronic/Acute contribution", state="running")
        fig_class = get_chronic_vs_acute_counts(medications, poly_days, med_class_map)

        status.update(label="Step 7: Duration Categories calculation", state="running")
        fig_dur = get_duration_categories(poly_summary)
        
        status.update(label="Step 8: Co-occurrence analysis", state="running")
        cooc_df = compute_med_cooccurrence_cached(medications, poly_days)

        status.update(label="Step 9: Poly by class", state="running")
        by_class = get_poly_by_class(medications, poly_days, med_class_map)

    # ================================
    #            KPI SECTION
    # ================================
    total_patients = patients["id"].nunique()
    patients_with_meds = medications["PATIENT"].nunique()
    patients_with_poly = poly_summary["PATIENT"].nunique()

    c1, c2, c3 = st.columns(3)
    c1.metric("Patients (filtered cohort)", total_patients)
    c2.metric("Patients with ≥1 medication", patients_with_meds)
    c3.metric(f"Patients with ≥{poly_threshold} concurrent meds", patients_with_poly)

    # ================================
    #    1 — Max concurrent histogram
    # ================================
    if not poly_summary.empty:
        fig_max = px.histogram(
            poly_summary, x="max_concurrent", nbins=10,
            title=f"Max Concurrent Medications (≥{poly_threshold})"
        )
        st.plotly_chart(fig_max, use_container_width=True)
    else:
        st.info("No patients reached this polypharmacy threshold.")

    # ================================
    #    2 — Time Trend (cached)
    # ================================
    if not poly_days.empty:
        pts_per_day = (
            poly_days.groupby("day")["PATIENT"]
            .nunique()
            .reset_index(name="patients_in_polypharmacy")
        )
        fig_time = px.line(
            pts_per_day,
            x="day", y="patients_in_polypharmacy",
            title="Polypharmacy Over Time"
        )
        st.plotly_chart(fig_time, use_container_width=True)

    # ================================
    #    3 — Top meds in polypharmacy
    # ================================
    if not top_meds.empty:
        fig_top = px.bar(
            top_meds.head(15),
            x="DESCRIPTION", y="patient_count",
            title="Top Medications in Polypharmacy Periods"
        )
        fig_top.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_top, use_container_width=True)

    # ================================
    #    4 — Polypharmacy by age group
    # ================================
    st.subheader("Polypharmacy by Age Group")
    st.plotly_chart(age_fig, use_container_width=True)

    # ================================
    #    5 — Chronic vs Acute meds
    # ================================
    st.subheader("Chronic vs Acute Medication Contribution")
    st.plotly_chart(fig_class, use_container_width=True)

    # ================================
    #    6 — Polypharmacy Duration Categories
    # ================================
    st.subheader("Polypharmacy Duration Categories")
    st.plotly_chart(fig_dur, use_container_width=True)

    # ================================
    #    TABLE — Poly Summary
    # ================================
    with st.expander("View per-patient polypharmacy summary"):
        st.dataframe(poly_summary)

    # ================================
    #    TIMELINE EXPORT
    # ================================
    st.markdown("---")
    st.subheader("Medication Timeline Export")
    poly_patients = poly_summary["PATIENT"].unique().tolist()
    poly_meds = medications[medications["PATIENT"].isin(poly_patients)]
    st.download_button(
        "Download Polypharmacy Medication Timeline (CSV)",
        poly_meds.to_csv(index=False),
        "polypharmacy_medications.csv"
    )

    # ================================
    #    PATIENT GANTT
    # ================================
    st.subheader("Patient-Level Timeline")
    selected_patient = st.selectbox(
        "Select patient:", options=poly_summary["PATIENT"].tolist()
    )

    timeline_df = get_patient_timeline(medications, selected_patient, med_class_map)
    if not timeline_df.empty:
        fig_gantt = px.timeline(
            timeline_df, x_start="Start", x_end="Finish", y="Task", color="class"
        )
        fig_gantt.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_gantt, use_container_width=True)

    # ================================
    #    7 — Co-occurrence
    # ================================
    st.subheader("Medication Co-Occurrence")
    
    if not cooc_df.empty:
        st.dataframe(cooc_df.head(30))
        fig_pairs = px.bar(
            cooc_df.head(20),
            x="count",
            y=cooc_df.head(20)["pair"],
            orientation="h",
            title="Top Co-Occurrence Pairs"
        )
        st.plotly_chart(fig_pairs, use_container_width=True)
    else:
        st.info("No co-occurrence pairs.")
    
    # ================================ Poly By Class Insights(Theurapatic classification) (coming from the utils/medication_analytics)==========
    meds_by_class = get_poly_by_class(medications, poly_days, med_class_map)

    # ================================ Poly By Age Breakdown Insights (coming from the utils/medication_analytics)==========
    poly_by_age = get_age_band_breakdown(
        poly_summary,
        patients,
        return_data=True
    )

    chronic_vs_acute_df = get_chronic_vs_acute_counts(
        medications,
        poly_days,
        med_class_map,
        return_data=True
    )    

    med_insights = generate_medication_insights(
        patient_poly=poly_summary,
        by_age=poly_by_age,
        by_class=meds_by_class,
        chronic_vs_acute_df=chronic_vs_acute_df,
        top_meds=top_meds
    )

    st.session_state.medication_insights = med_insights  

    st.subheader("🧠 AI Insights – Medications")

    for ins in med_insights:
        if ins["severity"] == "high":
            st.warning(ins["message"])
        elif ins["severity"] == "medium":
            st.info(ins["message"])
        else:
            st.caption(ins["message"])  

if __name__ == "__main__":
    main()
