# utils/vitals.py
import pandas as pd
import numpy as np
import streamlit as st
from typing import Tuple

# --- canonical vital names we care about ---
VITAL_MAP = {
    "body height": "height_cm",
    "body weight": "weight_kg",
    "body temperature": "temp_c",
    "systolic blood pressure": "sbp",
    "diastolic blood pressure": "dbp",
    "heart rate": "hr",
    "respiratory rate": "rr",
    "oxygen saturation in arterial blood": "spo2",
    "oxygen saturation": "spo2",
    "pain severity": "pain_score",
    # labs that might be present (we keep but not primary)
    "hemoglobin": "hemoglobin",
    "hematocrit": "hematocrit",
    "leukocytes": "wbc",
    "platelets": "platelets",
    # add more as needed
}

# A small set of descriptions to keep as vitals (others can be filtered out)
VITAL_KEYS = set(VITAL_MAP.keys())

# Age bands function reused
def get_age_band(age: int) -> str:
    if pd.isna(age):
        return "Unknown"
    age = int(age)
    if age < 18:
        return "0-17"
    if age < 50:
        return "18-49"
    if age < 65:
        return "50-64"
    if age < 75:
        return "65-74"
    return "75+"

# ------------------------------
# Helper: normalize description text
# ------------------------------
def _normalize_desc(s: str) -> str:
    if pd.isna(s):
        return ""
    return str(s).strip().lower()

# ------------------------------
# 1. Load & clean observations (call this with the observations dataframe)
# ------------------------------
@st.cache_data(show_spinner=False)
def clean_vitals(obs_df: pd.DataFrame) -> pd.DataFrame:
    """
    Input: observations dataframe with columns:
      DATE, PATIENT, ENCOUNTER, CATEGORY, CODE, DESCRIPTION, VALUE, UNITS, TYPE
    Output: tidy vitals DataFrame:
      DATE (datetime), PATIENT, ENCOUNTER, vital (canonical), value (numeric/string), units
    """
    if obs_df is None or obs_df.empty:
        return pd.DataFrame(columns=["DATE", "PATIENT", "ENCOUNTER", "vital", "value", "units", "raw_desc"])

    df = obs_df.copy()

    # normalize columns (safe access)
    df.columns = [c.strip().upper() for c in df.columns]

    # ensure expected columns
    for c in ["DATE", "PATIENT", "ENCOUNTER", "DESCRIPTION", "VALUE", "UNITS"]:
        if c not in df.columns:
            df[c] = None

    # lower description
    df["DESCRIPTION_CLEAN"] = df["DESCRIPTION"].astype(str).str.lower().str.strip()

    # map description to canonical vital (best-effort substring)
    def map_to_vital(desc: str):
        d = desc.lower()
        # direct match
        for k in VITAL_KEYS:
            if k in d:
                return VITAL_MAP[k]
        # partials
        if "systolic" in d:
            return "sbp"
        if "diastolic" in d:
            return "dbp"
        if "blood pressure" in d and "systolic" not in d and "diastolic" not in d:
            # sometimes BP stored as single value; skip
            return None
        if "temperature" in d or "temp" in d:
            return "temp_c"
        if "heart rate" in d or "pulse" in d:
            return "hr"
        if "respiratory rate" in d or "resp rate" in d:
            return "rr"
        if "oxygen saturation" in d or "spo2" in d or "o2 saturation" in d:
            return "spo2"
        if "weight" in d and "for-length" not in d:
            return "weight_kg"
        if "height" in d:
            return "height_cm"
        if "pain severity" in d:
            return "pain_score"
        # labs (basic)
        if "hemoglobin" in d:
            return "hemoglobin"
        if "hematocrit" in d:
            return "hematocrit"
        if "leukocytes" in d or "white blood" in d:
            return "wbc"
        if "platelet" in d:
            return "platelets"
        return None

    df["vital"] = df["DESCRIPTION_CLEAN"].apply(map_to_vital)

    # keep only rows mapped to vitals
    df = df[df["vital"].notna()].copy()

    # parse dates
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")

    # coerce numeric when possible (VALUE might be string)
    def try_numeric(v):
        if pd.isna(v):
            return np.nan
        try:
            # many Synthea values like "120.0" or "98" or "96%"
            s = str(v).strip()
            s = s.replace("%", "")
            s = s.replace(",", "")
            return float(s)
        except:
            return np.nan

    df["value_num"] = df["VALUE"].apply(try_numeric)
    df["UNITS"] = df["UNITS"].astype(str).str.strip().str.lower().replace("nan", "")

    # basic unit normalization (height, weight, temp)
    # Height: if unit contains 'cm' or 'cent', fine; if 'in' convert to cm
    def normalize_height(row):
        u = row["UNITS"]
        v = row["value_num"]
        if pd.isna(v):
            return np.nan
        if "cm" in u or "centimeter" in u:
            return v
        if "in" in u:
            return v * 2.54
        # if unit missing but typical number > 3 and < 3.0? ambiguous; assume cm if > 50
        if v > 3 and v < 300:
            # if v looks like cm already
            return v
        return np.nan

    df.loc[df["vital"] == "height_cm", "value_norm"] = df[df["vital"] == "height_cm"].apply(normalize_height, axis=1)

    # Weight: kg vs lb
    def normalize_weight(row):
        u = row["UNITS"]
        v = row["value_num"]
        if pd.isna(v):
            return np.nan
        if "kg" in u:
            return v
        if "lb" in u or "lb." in u or "pound" in u:
            return v * 0.45359237
        # assume kg if reasonable
        if 2 < v < 300:
            return v
        return np.nan

    df.loc[df["vital"] == "weight_kg", "value_norm"] = df[df["vital"] == "weight_kg"].apply(normalize_weight, axis=1)

    # Temperature: often in C or F
    def normalize_temp(row):
        u = row["UNITS"]
        v = row["value_num"]
        if pd.isna(v):
            return np.nan
        if "c" in u and "f" not in u:
            return v
        if "f" in u:
            return (v - 32.0) * 5.0 / 9.0
        # if unit missing: guess if > 45 then it's F (e.g. 98F) else C
        if v > 45:
            return (v - 32.0) * 5.0 / 9.0
        return v

    df.loc[df["vital"] == "temp_c", "value_norm"] = df[df["vital"] == "temp_c"].apply(normalize_temp, axis=1)

    # SPO2: percent
    def normalize_spo2(row):
        v = row["value_num"]
        if pd.isna(v):
            return np.nan
        if v > 1 and v <= 100:
            return v
        # sometimes 0-1 scale
        if 0 < v <= 1:
            return v * 100
        return np.nan

    df.loc[df["vital"] == "spo2", "value_norm"] = df[df["vital"] == "spo2"].apply(normalize_spo2, axis=1)

    # HR, RR, BP: use value_num as-is
    numeric_vitals = ["hr", "rr", "sbp", "dbp", "pain_score",
                      "hemoglobin", "hematocrit", "wbc", "platelets",
                      "mc v", "mch", "mchc"]
    df.loc[df["vital"].isin(["hr", "rr", "sbp", "dbp", "pain_score",
                             "hemoglobin", "hematocrit", "wbc", "platelets"]), "value_norm"] = \
        df.loc[df["vital"].isin(["hr", "rr", "sbp", "dbp", "pain_score",
                                 "hemoglobin", "hematocrit", "wbc", "platelets"]), "value_num"]

    # final tidy
    tidy = df[["DATE", "PATIENT", "ENCOUNTER", "vital", "value_norm", "UNITS", "DESCRIPTION"]].copy()
    tidy = tidy.rename(columns={"value_norm": "value", "UNITS": "units", "DESCRIPTION": "raw_desc"})
    tidy = tidy.sort_values(["PATIENT", "DATE"])

    # keep only rows with non-null value
    tidy = tidy[tidy["value"].notna()].reset_index(drop=True)

    return tidy


# ------------------------------
# 2. Latest vitals per patient (snapshot)
# ------------------------------
@st.cache_data(show_spinner=False)
def get_latest_vitals_cached(vitals_tidy: pd.DataFrame) -> pd.DataFrame:
    """
    For each patient and vital type, return the most recent record
    """
    if vitals_tidy is None or vitals_tidy.empty:
        return pd.DataFrame()

    df = vitals_tidy.copy()
    df = df.sort_values(["PATIENT", "vital", "DATE"])
    latest = df.groupby(["PATIENT", "vital"]).tail(1)
    latest = latest.reset_index(drop=True)
    # pivot so each row = patient with columns for vital types
    pivot = latest.pivot_table(index="PATIENT", columns="vital", values="value", aggfunc="last")
    pivot = pivot.reset_index()
    return pivot


# ------------------------------
# 3. BMI calculator (requires latest height & weight)
# ------------------------------
@st.cache_data(show_spinner=False)
def compute_bmi_cached(latest_vitals: pd.DataFrame) -> pd.DataFrame:
    """
    Input: pivot table from get_latest_vitals_cached()
    Returns: DataFrame with PATIENT and BMI and BMI category
    """
    if latest_vitals is None or latest_vitals.empty:
        return pd.DataFrame(columns=["PATIENT", "bmi", "bmi_cat"])

    df = latest_vitals.copy()
    # ensure columns presence
    if "height_cm" not in df.columns or "weight_kg" not in df.columns:
        df["bmi"] = np.nan
        df["bmi_cat"] = np.nan
        return df[["PATIENT", "bmi", "bmi_cat"]]

    h = df["height_cm"] / 100.0
    w = df["weight_kg"]
    bmi = w / (h * h)
    df["bmi"] = bmi
    def cat(b):
        try:
            if np.isnan(b): return np.nan
            if b < 18.5: return "Underweight"
            if b < 25: return "Normal"
            if b < 30: return "Overweight"
            return "Obese"
        except:
            return np.nan
    df["bmi_cat"] = df["bmi"].apply(cat)
    return df[["PATIENT", "bmi", "bmi_cat"]]


# ------------------------------
# 4. Clinical flags (per patient latest snapshot)
# ------------------------------
@st.cache_data(show_spinner=False)
def compute_clinical_flags(latest_vitals_pivot: pd.DataFrame, bmi_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Input: pivot table from get_latest_vitals_cached + optional BMI table
    Returns: DataFrame with boolean flags (tachycardia, bradycardia, fever, hypoxia, hypertension, hypotension)
    """
    if latest_vitals_pivot is None or latest_vitals_pivot.empty:
        return pd.DataFrame()

    df = latest_vitals_pivot.copy().set_index("PATIENT")
    flags = pd.DataFrame(index=df.index)

    # HR
    if "hr" in df.columns:
        flags["tachycardia"] = df["hr"] > 100
        flags["bradycardia"] = df["hr"] < 60
    else:
        flags["tachycardia"] = False
        flags["bradycardia"] = False

    # BP
    sbp = df["sbp"] if "sbp" in df.columns else pd.Series(index=df.index, dtype=float)
    dbp = df["dbp"] if "dbp" in df.columns else pd.Series(index=df.index, dtype=float)
    flags["hypertension"] = (sbp >= 140) | (dbp >= 90)
    flags["hypotension"] = (sbp < 90) | (dbp < 60)

    # Temp
    if "temp_c" in df.columns:
        flags["fever"] = df["temp_c"] >= 38.0
    else:
        flags["fever"] = False

    # SpO2
    if "spo2" in df.columns:
        flags["hypoxia"] = df["spo2"] < 94
    else:
        flags["hypoxia"] = False

    # BMI categories
    if bmi_df is not None and not bmi_df.empty:
        bmi_df = bmi_df.set_index("PATIENT")
        flags = flags.join(bmi_df[["bmi", "bmi_cat"]], how="left")
    else:
        flags["bmi"] = np.nan
        flags["bmi_cat"] = np.nan

    flags = flags.reset_index().rename(columns={"index": "PATIENT"})
    return flags


# ------------------------------
# 5. Trend / time-series aggregation
# ------------------------------
@st.cache_data(show_spinner=False)
def vitals_trend_cached(vitals_tidy: pd.DataFrame, vital_name: str, freq: str = "W") -> pd.DataFrame:
    """
    Aggregate mean/median per period for a given vital (freq = 'D','W','M')
    """
    if vitals_tidy is None or vitals_tidy.empty:
        return pd.DataFrame()
    df = vitals_tidy[vitals_tidy["vital"] == vital_name].copy()
    df = df[["DATE", "value"]].dropna()
    if df.empty:
        return pd.DataFrame()
    df = df.set_index("DATE").resample(freq)["value"].agg(["median", "mean", "count"])
    df = df.reset_index()
    return df


# ------------------------------
# 6. Patient vitals timeline
# ------------------------------
@st.cache_data(show_spinner=False)
def patient_vitals_timeline_cached(vitals_tidy: pd.DataFrame, patient_id: str) -> pd.DataFrame:
    if vitals_tidy is None or vitals_tidy.empty:
        return pd.DataFrame()
    df = vitals_tidy[vitals_tidy["PATIENT"] == patient_id].copy()
    if df.empty:
        return pd.DataFrame()
    # pivot for timeline visualization if required
    return df.sort_values("DATE")


# ------------------------------
# 7. Abnormal summary (cohort)
# ------------------------------
@st.cache_data(show_spinner=False)
def get_abnormal_vitals_summary(vitals_tidy: pd.DataFrame, patients_df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns counts and percentages of patients with abnormal flags across cohort.
    """
    latest = get_latest_vitals_cached(vitals_tidy)
    bmi = compute_bmi_cached(latest)
    flags = compute_clinical_flags(latest, bmi)
    # merge baseline patient info
    if patients_df is not None and not patients_df.empty:
        flags = flags.merge(patients_df[["id", "age"]].rename(columns={"id": "PATIENT"}), on="PATIENT", how="left")
        flags["age_band"] = flags["age"].apply(get_age_band)
    return flags


# ------------------------------
# 8. NEWS2 score (basic)
# ------------------------------
def _score_resp(rr):
    if pd.isna(rr): return 0
    try:
        rr = float(rr)
    except: return 0
    if rr <= 8: return 3
    if rr <= 11: return 1
    if rr <= 20: return 0
    if rr <= 29: return 2
    return 3

def _score_o2(spo2):
    if pd.isna(spo2): return 0
    try:
        s = float(spo2)
    except: return 0
    if s <= 91: return 3
    if s <= 93: return 2
    if s <= 95: return 1
    return 0

def _score_temp(temp):
    if pd.isna(temp): return 0
    try:
        t = float(temp)
    except: return 0
    if t < 36: return 1
    if t <= 38: return 0
    if t < 39: return 1
    return 2

def _score_sbp(sbp):
    if pd.isna(sbp): return 0
    try:
        s = float(sbp)
    except: return 0
    if s <= 90: return 3
    if s <= 100: return 2
    if s <= 110: return 1
    if s <= 219: return 0
    return 3

def _score_hr(hr):
    if pd.isna(hr): return 0
    try:
        h = float(hr)
    except: return 0
    if h <= 40: return 3
    if h <= 50: return 1
    if h <= 90: return 0
    if h <= 110: return 1
    if h <= 130: return 2
    return 3

@st.cache_data(show_spinner=False)
def compute_news2_score(latest_vitals_pivot: pd.DataFrame) -> pd.DataFrame:
    """
    Compute NEWS2 score per patient using latest vitals pivot.
    """
    if latest_vitals_pivot is None or latest_vitals_pivot.empty:
        return pd.DataFrame()
    df = latest_vitals_pivot.set_index("PATIENT") if "PATIENT" in latest_vitals_pivot.columns else latest_vitals_pivot.set_index(latest_vitals_pivot.index)
    res = []
    for pid, row in df.iterrows():
        rr = row.get("rr", np.nan)
        spo2 = row.get("spo2", np.nan)
        temp = row.get("temp_c", np.nan)
        sbp = row.get("sbp", np.nan)
        hr = row.get("hr", np.nan)
        score = (
            _score_resp(rr) + _score_o2(spo2) + _score_temp(temp) + _score_sbp(sbp) + _score_hr(hr)
        )
        res.append({"PATIENT": pid, "news2": score})
    return pd.DataFrame(res)
