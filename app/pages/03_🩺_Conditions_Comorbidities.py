import sys
import os
import streamlit as st
import plotly.express as px
from components.filters import render_global_filters

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from components.filters import render_global_filters
from utils.data_access import get_filtered_data

# Show sidebar filters (persistent)
render_global_filters(st.session_state.patients,
                      st.session_state.encounters,
                      read_only=True)

(
    patients,
    encounters,
    conditions,
    medications,
    procedures,
    immunizations,
    observations,
) = get_filtered_data()

#from utils.load_data import load_patients, load_conditions
from utils.clinical_analytics import compute_condition_statistics

with st.sidebar:
    st.info("Filters can only be modified on the Home page.")

st.title("🩺 Conditions & Comorbidities")
st.write("DEBUG gender:", st.session_state.get("gender_filter"))
st.write("DEBUG age_range:", st.session_state.get("age_range"))

#patients = st.session_state.filtered_patients
#conditions = st.session_state.filtered_conditions

stats = compute_condition_statistics(conditions, patients)

# ---- Top Conditions Chart ----
st.subheader("Top 10 Conditions by Frequency")

top_conditions = stats["top_conditions"]
cond_names = list(top_conditions.keys())
cond_counts = list(top_conditions.values())

fig1 = px.bar(
    x=cond_names,
    y=cond_counts,
    labels={"x": "Condition", "y": "Number of Patients"},
    title="Most Common Conditions",
)
fig1.update_layout(xaxis_tickangle=-45)

st.plotly_chart(fig1, width='stretch')

# ---- Multimorbidity Distribution ----
st.subheader("Multimorbidity Distribution")

multi_dist = stats["multimorbidity_distribution"]
multi_counts = list(multi_dist.keys())
multi_freqs = list(multi_dist.values())

fig2 = px.bar(
    x=multi_counts,
    y=multi_freqs,
    labels={"x": "Number of Concurrent Conditions", "y": "Patient Count"},
    title="Patients With Multiple Chronic Conditions",
)

st.plotly_chart(fig2, use_container_width=True)

# ---- Age vs Condition Burden ----
st.subheader("Average Number of Conditions per Age Group")

age_cond = stats["age_condition_distribution"]

fig3 = px.bar(
    x=list(age_cond.keys()),
    y=list(age_cond.values()),
    labels={"x": "Age Group", "y": "Avg Chronic Conditions"},
    title="Condition Burden Increases with Age",
)

st.plotly_chart(fig3, width='stretch')
