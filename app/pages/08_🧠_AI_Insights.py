import sys
import os
import streamlit as st
from collections import defaultdict


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)


from utils.ai_insight_registry import collect_all_insights
from utils.ai_utils import bucket_insights_by_severity
from app.nlp.insight_engine import generate_insight


st.set_page_config(page_title="AI Insights", layout="wide")
st.title("🧠 AI Insights – Healthcare Analytics")

# -----------------------------------
# Pull insights from session_state
# -----------------------------------
procedure_insights = st.session_state.get("procedure_insights", [])
immunization_insights = st.session_state.get("immunization_insights", [])
medication_insights = st.session_state.get("medication_insights", [])

all_insights = collect_all_insights(
    procedure_insights,
    immunization_insights,
    medication_insights
)

# st.write([(i["domain"], i["signal"]) for i in all_insights])

if not all_insights:
    st.info("No AI insights available yet.")
    st.stop()

buckets = bucket_insights_by_severity(all_insights)

if buckets["high"]:
    st.subheader("🚨 High Priority Signals")
    for ins in buckets["high"]:
        st.error(f"[{ins['domain'].title()}] {ins['message']}")

if buckets["medium"]:
    st.subheader("⚠️ Medium Priority Signals")
    for ins in buckets["medium"]:
        st.warning(f"[{ins['domain'].title()}] {ins['message']}")

if buckets["low"]:
    st.subheader("ℹ️ Informational Signals")
    for ins in buckets["low"]:
        st.info(f"[{ins['domain'].title()}] {ins['message']}")

def group_insights_by_domain(insights):
    grouped = defaultdict(list)
    for ins in insights:
        grouped[ins["domain"]].append(ins["message"])
    return grouped

def prepare_llm_metrics(insights):
    grouped = group_insights_by_domain(insights)

    structured_metrics = {
        "procedures": grouped.get("procedures", []),
        "immunizations": grouped.get("immunizations", []),
        "medications": grouped.get("medications", []),
    }

    return structured_metrics

if st.checkbox("🧠 Generate Executive AI Summary"):
    llm_metrics = prepare_llm_metrics(all_insights)

    with st.spinner("Generating executive summary..."):
        summary = generate_insight(
            metrics=llm_metrics,
            persona="executive"   # 👈 key change
        )

    st.subheader("📊 Executive AI Summary")
    st.success(summary)


