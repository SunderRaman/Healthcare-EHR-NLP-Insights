import streamlit as st
import pandas as pd
import sys
import os

# Add project root to PYTHONPATH so utils/ can be imported
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from components.filters import render_global_filters
from utils.data_access import get_filtered_data

from utils.clinical_analytics import (
    compute_condition_statistics,
    compute_medication_statistics,
    compute_procedure_statistics,
    compute_immunization_statistics,
    compute_observation_statistics
)

from utils.analytics import compute_utilization_metrics
from nlp.insight_engine import generate_insight

from charts.utilization_charts import (
    encounter_volume_over_time,
    encounter_type_distribution,
    age_distribution,
    gender_distribution
)
# Show sidebar filters (persistent)
render_global_filters(st.session_state.patients,
                      st.session_state.encounters,
                      read_only=True)


# Retrieve filtered datasets
(
    patients,
    encounters,
    conditions,
    medications,
    procedures,
    immunizations,
    observations,
) = get_filtered_data()

with st.sidebar:
    st.info("Filters can only be modified on the Home page.")

st.title("📊 Utilization Analytics")
st.metric("Total Encounters", len(encounters))
st.metric("Unique Patients", len(patients))
st.write("DEBUG gender:", st.session_state.get("gender_filter"))
st.write("DEBUG age_range:", st.session_state.get("age_range"))


persona = st.sidebar.selectbox(
    "Insight Style",
    ["Clinical", "Executive", "Analyst"]
)

persona_key = persona.lower()

# Display charts
# st.subheader("Encounter Trends")
st.plotly_chart(encounter_volume_over_time(encounters), width='stretch')

col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(encounter_type_distribution(encounters), width='stretch')

with col2:
    st.plotly_chart(gender_distribution(patients), width='stretch')

st.subheader("Age Demographics")
st.plotly_chart(age_distribution(patients), width='stretch')

@st.cache_data(show_spinner=False)
def cached_insight(metrics, persona_key):
    return generate_insight(metrics, persona_key)

st.markdown("---")
st.header("🧠 AI-Generated Clinical Insights")
with st.spinner("Generating insights..."):
    metrics = compute_utilization_metrics(patients, encounters)
    insight_text = cached_insight(metrics, persona_key)

st.write(insight_text)

st.markdown("---")
st.header("📊 Clinical Analytics")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Conditions",
    "Medications",
    "Procedures",
    "Immunizations",
    "Observations"
])

with tab1:
    cond_stats = compute_condition_statistics(conditions, patients)
    st.subheader("Top Conditions")
    st.write(cond_stats["top_conditions"])
    st.subheader("Multimorbidity Distribution")
    st.write(cond_stats["multimorbidity_distribution"])
    st.subheader("Avg Conditions per Age Group")
    st.write(cond_stats["age_condition_distribution"])

with tab2:
    med_stats = compute_medication_statistics(medications)
    st.subheader("Polypharmacy Rate (%)")
    st.write(med_stats["polypharmacy_rate"])
    st.subheader("Medication Count Distribution")
    st.write(med_stats["medication_distribution"])

with tab3:
    proc_stats = compute_procedure_statistics(procedures)
    st.subheader("Top Procedures")
    st.write(proc_stats["top_procedures"])

with tab4:
    imm_stats = compute_immunization_statistics(immunizations, patients)
    st.subheader("Immunization Rate (%)")
    st.write(imm_stats["immunization_rate"])

with tab5:
    obs_stats = compute_observation_statistics(observations)
    st.subheader("Most Frequent Observations")
    st.write(obs_stats["top_observations"])

# -----------------------------
# st.sidebar.markdown("---")
# st.sidebar.subheader("Clinical Dataset Overview")

# st.sidebar.write(f"🩺 Conditions: **{len(conditions)}**")
# st.sidebar.write(f"💊 Medications: **{len(medications)}**")
# st.sidebar.write(f"🏥 Procedures: **{len(procedures)}**")
# st.sidebar.write(f"💉 Immunizations: **{len(immunizations)}**")
# st.sidebar.write(f"🧪 Observations: **{len(observations)}**")

# st.markdown("---")
# st.header("Clinical Linkage Validation")

# st.write("Conditions linked:", conditions["PATIENT"].isin(patients["id"]).mean())
# st.write("Medications linked:", medications["PATIENT"].isin(patients["id"]).mean())
# st.write("Procedures linked:", procedures["PATIENT"].isin(patients["id"]).mean())
# st.write("Immunizations linked:", immunizations["PATIENT"].isin(patients["id"]).mean())
# st.write("Observations linked:", observations["PATIENT"].isin(patients["id"]).mean())