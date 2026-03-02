import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st

# ------------------------------------------------------
# 1. NEWS2 SCORING LOGIC
# ------------------------------------------------------

def score_rr(rr):
    if pd.isna(rr): return 0
    rr = float(rr)
    if rr <= 8: return 3
    if 9 <= rr <= 11: return 1
    if 12 <= rr <= 20: return 0
    if 21 <= rr <= 24: return 2
    return 3

def score_spo2(s):
    if pd.isna(s): return 0
    s = float(s)
    if s >= 96: return 0
    if 94 <= s <= 95: return 1
    if 92 <= s <= 93: return 2
    return 3

def score_temp(t):
    if pd.isna(t): return 0
    t = float(t)
    if t < 35.0: return 3
    if 35.0 <= t <= 36.0: return 1
    if 36.1 <= t <= 38.0: return 0
    if 38.1 <= t <= 39.0: return 1
    return 2

def score_sbp(bp):
    if pd.isna(bp): return 0
    bp = float(bp)
    if bp <= 90: return 3
    if 91 <= bp <= 100: return 2
    if 101 <= bp <= 110: return 1
    if 111 <= bp <= 219: return 0
    return 3

def score_hr(hr):
    if pd.isna(hr): return 0
    hr = float(hr)
    if hr <= 40: return 3
    if 41 <= hr <= 50: return 1
    if 51 <= hr <= 90: return 0
    if 91 <= hr <= 110: return 1
    if 111 <= hr <= 130: return 2
    return 3


# ------------------------------------------------------
# 2. MAIN NEWS2 COMPUTATION
# ------------------------------------------------------
@st.cache_data(show_spinner=False)
def compute_news2_scores(df_wide: pd.DataFrame) -> pd.DataFrame:
    df = df_wide.copy()

    # Apply scoring functions to your actual columns
    df["resp_score"] = df["rr"].apply(score_rr)
    df["spo2_score"] = df["spo2"].apply(score_spo2)
    df["temp_score"] = df["temp_c"].apply(score_temp)
    df["sysbp_score"] = df["sbp"].apply(score_sbp)
    df["hr_score"] = df["hr"].apply(score_hr)

    # Sum into NEWS2
    df["NEWS2"] = (
        df["resp_score"]
        + df["spo2_score"]
        + df["temp_score"]
        + df["sysbp_score"]
        + df["hr_score"]
    )

    return df


# ------------------------------------------------------
# 3. CORRELATION HEATMAP
# ------------------------------------------------------
@st.cache_data(show_spinner=False)
def compute_vitals_correlation(df_wide: pd.DataFrame):

    numeric_cols = [
        "sbp", "dbp", "hr", "rr", "spo2", "temp_c",
        "weight_kg", "height_cm",
        "hemoglobin", "hematocrit", "platelets", "wbc"
    ]

    # Drop missing columns safely
    available = [c for c in numeric_cols if c in df_wide.columns]

    corr = df_wide[available].corr()

    fig = px.imshow(
        corr,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="RdBu_r",
        title="Correlation Between Vital Signs & Labs"
    )
    return fig



# ------------------------------------------------------
# 4. NEWS2 TIMESERIES — for 1 patient
# ------------------------------------------------------
def plot_news2_timeseries(df_news: pd.DataFrame, patient: str):
    sub = df_news[df_news["PATIENT"] == patient]

    if sub["DATE"].nunique() < 3:
        return None  # Option B

    fig = px.line(
        sub,
        x="DATE",
        y="NEWS2",
        title=f"NEWS2 Time-Series for Patient {patient}",
        markers=True
    )
    fig.update_layout(yaxis=dict(range=[0, df_news["NEWS2"].max() + 1]))
    return fig


# ------------------------------------------------------
# 5. NEWS2 DISTRIBUTION FOR COHORT
# ------------------------------------------------------
def plot_news2_distribution(df_news: pd.DataFrame):
    fig = px.histogram(
        df_news,
        x="NEWS2",
        nbins=15,
        title="Distribution of NEWS2 Scores (Cohort)"
    )
    return fig
