import sys
import os
import streamlit as st

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from utils.load_data import load_patients, load_encounters

st.title("🏠 Overview Dashboard")

patients = load_patients()
encounters = load_encounters()

col1, col2 = st.columns(2)

with col1:
    st.metric("Total Patients", len(patients))

with col2:
    st.metric("Total Encounters", len(encounters))

st.markdown("---")

st.write("Use the left navigation menu to explore deeper analytics.")
