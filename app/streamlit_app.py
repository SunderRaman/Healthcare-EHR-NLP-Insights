import streamlit as st
import pandas as pd
import sys
import os

st.set_page_config(
    page_title="Healthcare EHR Clinical Analytics",
    page_icon="🏥",
    layout="wide"
)

# Add project root to PYTHONPATH so utils/ can be imported
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from components.filters import render_global_filters

# with st.sidebar:
#     st.markdown("""
#     ## 🏥 Healthcare EHR Analytics
#     ### Population Health Insights
#     ---
#     """)


from utils.load_data import (
    load_patients, load_encounters, load_conditions,
    load_medications, load_procedures, load_immunizations,
    load_observations
)
from utils.filters import apply_global_filters
from components.filters import render_global_filters



# ---- Load data once ----
if "patients" not in st.session_state:
    st.session_state.patients = load_patients()
    st.session_state.encounters = load_encounters()
    st.session_state.conditions = load_conditions()
    st.session_state.medications = load_medications()
    st.session_state.procedures = load_procedures()
    st.session_state.immunizations = load_immunizations()
    st.session_state.observations = load_observations()

# Working dataset handles
patients = st.session_state.patients
encounters = st.session_state.encounters

# ---- Sidebar Filters (global + persistent) ----
gender_filter, age_range, selected_encounter_types = render_global_filters(
    patients, encounters,read_only=False
)
# ---- Apply Filtering ----
(
    st.session_state.filtered_patients,
    st.session_state.filtered_encounters,
    st.session_state.filtered_conditions,
    st.session_state.filtered_medications,
    st.session_state.filtered_procedures,
    st.session_state.filtered_immunizations,
    st.session_state.filtered_observations,
) = apply_global_filters(
    patients,
    encounters,
    st.session_state.conditions,
    st.session_state.medications,
    st.session_state.procedures,
    st.session_state.immunizations,
    st.session_state.observations,
    gender_filter,
    age_range,
    selected_encounter_types
)

st.title("🏥 Healthcare EHR Analytics Platform")

st.markdown("""
    Welcome to the **Healthcare EHR Analytics Platform**.

    Use the navigation on the left to explore:
    - Utilization analytics
    - Clinical conditions & comorbidities
    - Medications & polypharmacy
    - Vitals and abnormal observations
    - Immunization coverage
    - Procedure utilization patterns
    - AI-generated clinical insights
    """
)


st.success("Global filters applied. Navigate to dashboards using the sidebar.")


