import sys
import os
import streamlit as st
from pathlib import Path
import pandas as pd
import plotly.express as px
from app.nlp.insight_engine import generate_insight
from utils.data_access import get_filtered_data

MAX_LABEL_LEN = 20

ROOT_DIR = Path(__file__).resolve().parent.parent
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from utils.load_data import (
    load_procedures,
    load_encounters,
    load_patients
)

from utils.clinical_analytics import (
    compute_procedure_features,
    generate_rule_based_insights
)

def main():
# --------------------------------------------------
# Page config
# --------------------------------------------------
    st.set_page_config(
    page_title="Procedures Utilization",
    layout="wide"
)

    st.title("🛠️ Procedures Utilization")

    # --------------------------------------------------
    # Load data
    # --------------------------------------------------
    with st.spinner("Loading data..."):
        # procedures = load_procedures()
        # encounters = load_encounters()
        # patients = load_patients()
        (
            patients,
            encounters,
            conditions,
            medications,
            procedures,
            immunizations,
            observations,
        ) = get_filtered_data()

    # --------------------------------------------------
    # Basic preprocessing
    # --------------------------------------------------
    procedures.loc[:,"year_month"] = (procedures["start"].dt.to_period("M").astype(str))

    # Join encounters
    procedures = procedures.merge(
        encounters[["id", "encounterclass"]],
        left_on="encounter",
        right_on="id",
        how="left"
    )

    # Join patients
    procedures = procedures.merge(
        patients[["id", "birthdate", "gender"]],
        left_on="patient",
        right_on="id",
        how="left",
        suffixes=("", "_patient")
    )

    procedures["age"] = (
        procedures["start"].dt.year - procedures["birthdate"].dt.year
    )

    # --------------------------------------------------
    # KPI Tiles
    # --------------------------------------------------
    st.subheader("📊 Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Procedures", f"{len(procedures):,}")
    col2.metric("Unique Patients", procedures["patient"].nunique())
    col3.metric("Unique Encounters", procedures["encounter"].nunique())
    col4.metric(
        "Avg Procedures / Encounter",
        round(len(procedures) / procedures["encounter"].nunique(), 2)
    )

    # --------------------------------------------------
    # Top Procedures by Volume
    # --------------------------------------------------
    st.subheader("🔝 Top Procedures by Volume")

    top_n = st.slider("Select Top N", 5, 25, 10)

    top_procedures = (
        procedures["description"]
        .value_counts()
        .head(top_n)
        .reset_index()
    )

    top_procedures.columns = ["Procedure", "Count"]

    top_procedures["label_short"] = (
        top_procedures["Procedure"]
        .str.slice(0, MAX_LABEL_LEN)
        .str.rstrip()
        + "…"
    )

    fig_top_proc = px.bar(
        top_procedures,
        x="Procedure",          # FULL unique value
        y="Count",
        text="Count",
        hover_name="Procedure"
    )

    fig_top_proc.update_layout(
        xaxis=dict(
            tickmode="array",
            tickvals=top_procedures["Procedure"],
            ticktext=top_procedures["label_short"],
            tickangle=45
        ),
        margin=dict(b=140)
    )

    st.plotly_chart(fig_top_proc, width='stretch')

    # --------------------------------------------------
    # Procedures Over Time
    # --------------------------------------------------
    st.subheader("📈 Procedures Over Time")

    time_series = (
        procedures
        .groupby("year_month")
        .size()
        .reset_index(name="count")
    )

    st.line_chart(
        time_series.set_index("year_month")
    )

    # --------------------------------------------------
    # Procedures by Encounter Type
    # --------------------------------------------------
    st.subheader("🏥 Procedures by Encounter Type")

    encounter_dist = (
        procedures["encounterclass"]
        .fillna("Unknown")
        .value_counts()
        .reset_index()
    )

    encounter_dist.columns = ["Encounter Type", "Count"]

    st.bar_chart(encounter_dist.set_index("Encounter Type"))

    # --------------------------------------------------
    # Procedure Cost Utilization
    # --------------------------------------------------
    st.subheader("💰 Procedure Cost Utilization")

    cost_by_proc = (
        procedures
        .groupby("description")["base_cost"]
        .agg(["sum", "mean", "count"])
        .reset_index()
        .sort_values("sum", ascending=False)
        .head(10)
    )

    st.dataframe(
        cost_by_proc.rename(
            columns={
                "description": "Procedure",
                "sum": "Total Cost",
                "mean": "Avg Cost",
                "count": "Count"
            }
        ).style.format({
            "Total Cost": "{:,.0f}",
            "Avg Cost": "{:,.2f}",
            "Count": "{:,}"
        }),
        width='stretch'
    )

    # --------------------------------------------------
    # Procedures by Clinical Reason
    # --------------------------------------------------
    st.subheader("🧠 Procedures by Clinical Reason")

    reason_dist = (
        procedures["reasondescription"]
        .dropna()
        .value_counts()
        .head(10)
        .reset_index()
    )

    reason_dist.columns = ["Reason", "Procedure Count"]

    reason_dist["reason_short"] = (
        reason_dist["Reason"]
        .str.slice(0, 20)
        .str.rstrip()
        + "…"
    )



    fig_reason = px.bar(
        reason_dist,
        x="reason_short",
        y="Procedure Count",
        hover_data={
            "Reason": True,
            "reason_short": False,
            "Procedure Count": True
        },
        labels={
            "reason_short": "Clinical Reason",
            "Procedure Count": "Procedure Count"
        }
    )

    fig_reason.update_layout(
        xaxis_tickangle=45,
        margin=dict(b=160)
    )

    fig_reason.update_traces(
        text=reason_dist["Procedure Count"],
        textposition="outside",
        cliponaxis=False
    )

    st.plotly_chart(fig_reason, width='stretch')

    # --------------------------------------------------
    # Patient-Level Procedure Timeline  
    # --------------------------------------------------

    st.subheader("🧑‍⚕️ Patient-Level Procedure Timeline (Event View)")

    patient_id = st.selectbox(
        "Select Patient",
        procedures["patient"].unique()
    )

    pt_df = procedures[procedures["patient"] == patient_id].copy()

    if not pt_df.empty:
        fig_event = px.scatter(
            pt_df,
            x="start",
            y="description",
            color="encounterclass",
            hover_name="description",
            hover_data={
                "encounterclass": True,
                "base_cost": True,
                "start": True
            }
        )

        fig_event.update_layout(
            xaxis_title="Date",
            yaxis_title="Procedure",
            height=450
        )

        st.plotly_chart(fig_event, width='stretch')
    else:
        st.info("No procedures found for selected patient.")

    # --------------------------------------------------
    # High Procedure Utilization Insights     
    # --------------------------------------------------

    st.subheader("🚨 High Procedure Utilization Patients")

    proc_per_patient = (
        procedures
        .groupby("patient")
        .size()
        .reset_index(name="procedure_count")
    )

    threshold = proc_per_patient["procedure_count"].quantile(0.95)

    fig_outliers = px.histogram(
        proc_per_patient,
        x="procedure_count",
        nbins=30
    )

    fig_outliers.add_vline(
        x=threshold,
        line_dash="dash",
        annotation_text="95th Percentile"
    )

    st.plotly_chart(fig_outliers, width='stretch')

    st.markdown(
        f"**High-utilization patients (>95th percentile):** "
        f"{(proc_per_patient['procedure_count'] > threshold).sum()}"
    )

    #--------------------------------------------------
    # High-Cost / Low-Volume Procedures & Acute vs Chronic  
    #--------------------------------------------------

    st.subheader("💸 High-Cost / Low-Volume Procedures")

    proc_cost = (
        procedures
        .groupby("description")
        .agg(
            total_cost=("base_cost", "sum"),
            count=("description", "count")
        )
        .reset_index()
    )

    fig_cost = px.scatter(
        proc_cost,
        x="count",
        y="total_cost",
        size="total_cost",
        hover_name="description",
        labels={
            "count": "Procedure Volume",
            "total_cost": "Total Cost"
        }
    )

    fig_cost.update_layout(height=500)

    st.plotly_chart(fig_cost, width='stretch')

    st.subheader("⏳ Acute vs Chronic Procedure Mix")

    #--------------------------------------------------
    # Acute vs Chronic Procedure Mix
    #--------------------------------------------------
    CHRONIC_KEYWORDS = [
        "screening", "assessment", "follow-up", "management"
    ]

    procedures["proc_type"] = procedures["description"].str.lower().apply(
        lambda x: "Chronic" if any(k in x for k in CHRONIC_KEYWORDS) else "Acute"
    )

    proc_type_dist = (
        procedures["proc_type"]
        .value_counts()
        .reset_index()
    )

    proc_type_dist.columns = ["Type", "Count"]

    fig_type = px.pie(
        proc_type_dist,
        names="Type",
        values="Count",
        hole=0.4
    )

    st.plotly_chart(fig_type, width='stretch')

    st.subheader("🧠 AI Insights – Procedures")

    patient_features = compute_procedure_features(procedures)
    insights = generate_rule_based_insights(patient_features)

    if insights:
        for insight in insights:
            st.info(insight["message"])
    else:
        st.success("No unusual procedure utilization patterns detected.")

    st.subheader("🤖 AI Narrative Summary (Procedures)")

    if st.button("Generate AI Summary"):
        with st.spinner("Generating AI insights..."):
            summary = generate_insight(insights)
            st.success(summary)
    
    st.session_state.procedure_insights = insights

if __name__ == "__main__":
    main()