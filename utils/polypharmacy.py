import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px


# ================================
# 1. Compute daily polypharmacy (cached)
# ================================
@st.cache_data(show_spinner=False)
def compute_daily_polypharmacy_cached(medications: pd.DataFrame, threshold: int):
    """
    ULTRA-FAST VERSION: O(N log N) interval sweep,
    NO exploding of dates.

    Returns:
        daily_counts: PATIENT, day, active_meds   (sparse form)
        poly_summary: PATIENT, max_concurrent, poly_days
    """
    if medications.empty:
        return (
            pd.DataFrame(columns=["PATIENT", "day", "active_meds"]),
            pd.DataFrame(columns=["PATIENT", "max_concurrent", "poly_days"]),
        )

    meds = medications.copy()
    meds["START"] = pd.to_datetime(meds["START"]).dt.normalize()
    meds["STOP"] = pd.to_datetime(meds["STOP"]).fillna(meds["START"]).dt.normalize()

    out_daily = []
    out_summary = {}

    # Process per patient using interval sweep
    for pid, grp in meds.groupby("PATIENT"):
        events = []  # (+1 at start, -1 at end+1)

        for _, row in grp.iterrows():
            start = row["START"]
            stop = row["STOP"] + pd.Timedelta(days=1)  # end+1

            events.append((start, +1))
            events.append((stop, -1))

        # Sort events by date
        events.sort()

        active = 0
        last_day = None
        patient_days = []  # only days where active changes

        for day, delta in events:
            if last_day is not None and last_day != day:
                # record previous segment
                patient_days.append((last_day, active))
            active += delta
            last_day = day

        # Last segment
        if last_day is not None:
            patient_days.append((last_day, active))

        # Convert to DataFrame
        dfp = pd.DataFrame(patient_days, columns=["day", "active_meds"])

        # Remove final day beyond stop (because stop+1 produces zero intervals)
        dfp = dfp[dfp["active_meds"] > 0]

        dfp["PATIENT"] = pid
        out_daily.append(dfp)

        # Compute summary
        max_con = dfp["active_meds"].max() if not dfp.empty else 0
        poly_days = dfp[dfp["active_meds"] >= threshold]["day"].nunique()

        out_summary[pid] = {
            "PATIENT": pid,
            "max_concurrent": int(max_con),
            "poly_days": int(poly_days),
        }

    # Final results
    daily_counts = pd.concat(out_daily, ignore_index=True) if out_daily else \
        pd.DataFrame(columns=["PATIENT", "day", "active_meds"])

    poly_summary = pd.DataFrame.from_dict(out_summary, orient="index")

    return daily_counts, poly_summary



# ================================
# 2. Enrich poly_summary with age & other metadata (cached)
# ================================
@st.cache_data(show_spinner=False)
def enrich_poly_summary_cached(poly_summary: pd.DataFrame, patients: pd.DataFrame):
    if poly_summary.empty:
        return poly_summary

    summary = poly_summary.merge(
        patients[["id", "age"]].rename(columns={"id": "PATIENT"}),
        on="PATIENT",
        how="left"
    )
    return summary


# ================================
# 3. Get poly-days (cached)
# ================================
@st.cache_data(show_spinner=False)
def get_poly_days_cached(daily_counts: pd.DataFrame, threshold: int):
    if daily_counts.empty:
        return pd.DataFrame()
    return daily_counts[daily_counts["active_meds"] >= threshold]


# ================================
# 4. Top medications during polypharmacy (cached)
# ================================
@st.cache_data(show_spinner=False)
def get_top_meds_cached(
    medications: pd.DataFrame,
    poly_days: pd.DataFrame,
    return_data: bool = True
):
    """
    FAST VERSION — NO DATE EXPLOSION.
    Finds medications whose intervals overlap with polypharmacy days.

    Returns Top medications = unique patients exposed to each medication
    during their polypharmacy periods.
    """
    if medications.empty or poly_days.empty:
        return pd.DataFrame()

    # Convert to date boundaries
    meds = medications.copy()
    meds["START"] = pd.to_datetime(meds["START"]).dt.normalize()
    meds["STOP"] = pd.to_datetime(meds["STOP"]).fillna(meds["START"]).dt.normalize()

    # Compute per-patient polypharmacy ranges
    poly_ranges = (
        poly_days.groupby("PATIENT")
        .agg(poly_start=("day", "min"), poly_end=("day", "max"))
        .reset_index()
    )

    # Merge medication intervals with poly ranges per patient
    merged = meds.merge(poly_ranges, on="PATIENT", how="inner")

    # Keep only intervals that overlap:
    # (med_start <= poly_end) AND (med_end >= poly_start)
    mask = (
        (merged["STOP"] >= merged["poly_start"]) &
        (merged["START"] <= merged["poly_end"])
    )
    overlapped = merged[mask]

    if overlapped.empty:
        return pd.DataFrame()

    # Count unique patients exposed to each medication
    top_meds = (
        overlapped.groupby("DESCRIPTION")["PATIENT"]
        .nunique()
        .reset_index(name="patient_count")
        .sort_values("patient_count", ascending=False)
    )

    # Return data directly for AI / analytics
    return top_meds

# ================================
# 5. Age-band distribution chart
# ================================
def get_age_band(age: int) -> str:
    if age < 18:
        return "0-17"
    elif age < 50:
        return "18-49"
    elif age < 65:
        return "50-64"
    elif age < 75:
        return "65-74"
    else:
        return "75+"


def get_age_band_breakdown(
    poly_summary: pd.DataFrame,
    patients: pd.DataFrame,
    return_data: bool = False
):
    if poly_summary.empty:
        if return_data:
            return pd.DataFrame()
        return px.bar(title="No polypharmacy data")

    age_counts = (
        poly_summary.groupby("age_band")["PATIENT"]
        .nunique()
        .reset_index(name="poly_patients")
    )

    cohort = patients.copy()
    cohort["age_band"] = cohort["age"].astype(int).apply(get_age_band)

    cohort_counts = (
        cohort.groupby("age_band")["id"]
        .nunique()
        .reset_index(name="cohort_patients")
    )

    merged = age_counts.merge(cohort_counts, on="age_band", how="left")
    merged["poly_pct"] = (merged["poly_patients"] / merged["cohort_patients"]) * 100

    if return_data:
        return merged

    fig = px.bar(
        merged,
        x="age_band",
        y="poly_pct",
        title="Polypharmacy (%) by Age Group",
        labels={"poly_pct": "Polypharmacy %", "age_band": "Age Group"},
    )

    return fig



# ================================
# 6. Chronic vs Acute contribution (cached)
# ================================
def classify_medication(description: str, code: str, mapping_df: pd.DataFrame) -> str:
    """
    Uses your ATC-mapping file to classify a medication.
    """
    desc = str(description).lower()
    code = str(code)

    if not mapping_df.empty and "CODE" in mapping_df.columns:
        row = mapping_df[mapping_df["CODE"].astype(str) == code]
        if not row.empty:
            flag = row["CHRONIC_FLAG"].iloc[0].lower()
            return "chronic" if "chronic" in flag else "acute"

    return "acute"


@st.cache_data(show_spinner=False)
def get_chronic_vs_acute_counts(
    medications,
    poly_days,
    med_class_map,
    return_data: bool = False
):
    """
    FAST VERSION — NO DATE EXPLOSION.

    Computes chronic vs acute medication involvement
    by checking interval overlap with polypharmacy days.
    """

    if medications.empty or poly_days.empty:
        if return_data:
            return pd.DataFrame()
        return px.bar(title="No polypharmacy days")

    min_day = poly_days["day"].min()
    max_day = poly_days["day"].max()

    meds = medications.copy()
    meds["START"] = pd.to_datetime(meds["START"]).dt.normalize()
    meds["STOP"] = pd.to_datetime(meds["STOP"]).fillna(meds["START"]).dt.normalize()

    meds = meds[(meds["STOP"] >= min_day) & (meds["START"] <= max_day)]

    meds["class"] = meds.apply(
        lambda r: classify_medication(r["DESCRIPTION"], r["CODE"], med_class_map),
        axis=1
    )

    poly_ranges = (
        poly_days.groupby("PATIENT")
        .agg(start=("day", "min"), end=("day", "max"))
        .reset_index()
    )

    merged = meds.merge(poly_ranges, on="PATIENT", how="inner")

    merged = merged[
        (merged["STOP"] >= merged["start"]) &
        (merged["START"] <= merged["end"])
    ]

    if merged.empty:
        if return_data:
            return pd.DataFrame()
        return px.bar(title="No chronic/acute meds during polypharmacy")

    class_counts = (
        merged.groupby("class")["PATIENT"]
        .nunique()
        .reset_index(name="unique_patients")
    )

    if return_data:
        return class_counts

    fig = px.bar(
        class_counts,
        x="class",
        y="unique_patients",
        title="Chronic vs Acute Medications During Polypharmacy",
    )

    return fig



# ================================
# 7. Duration category breakdown
# ================================
def get_duration_categories(poly_summary: pd.DataFrame):
    if poly_summary.empty:
        return px.pie(title="No polypharmacy summary")

    dur_counts = (
        poly_summary.groupby("duration_category")["PATIENT"]
        .nunique()
        .reset_index(name="patients")
    )

    fig = px.pie(
        dur_counts,
        values="patients",
        names="duration_category",
        title="Polypharmacy Duration Categories"
    )

    return fig


# ================================
# 8. Patient medication timeline (Gantt)
# ================================
def get_patient_timeline(medications: pd.DataFrame, patient_id: str, mapping_df: pd.DataFrame):
    df = medications[medications["PATIENT"] == patient_id].copy()
    if df.empty:
        return pd.DataFrame()

    df["START"] = pd.to_datetime(df["START"])
    df["STOP"] = pd.to_datetime(df["STOP"]).fillna(df["START"])

    df["class"] = df.apply(
        lambda r: classify_medication(r["DESCRIPTION"], r["CODE"], mapping_df),
        axis=1
    )

    return df[["DESCRIPTION", "START", "STOP", "class", "CODE"]].rename(
        columns={"DESCRIPTION": "Task", "START": "Start", "STOP": "Finish"}
    )


# ================================
# 9. Medication co-occurrence (cached)
# ================================
@st.cache_data(show_spinner=False)
def compute_med_cooccurrence_cached(medications: pd.DataFrame, poly_days: pd.DataFrame):
    """
    FAST VERSION — NO DATE EXPLOSION.

    Returns medication co-occurrence pairs by checking interval overlap
    during polypharmacy periods for each patient.
    """

    if medications.empty or poly_days.empty:
        return pd.DataFrame(columns=["pair", "count"])

    meds = medications.copy()
    meds["START"] = pd.to_datetime(meds["START"]).dt.normalize()
    meds["STOP"] = pd.to_datetime(meds["STOP"]).fillna(meds["START"]).dt.normalize()

    # Compute per-patient polypharmacy window
    poly_ranges = (
        poly_days.groupby("PATIENT")
        .agg(poly_start=("day", "min"), poly_end=("day", "max"))
        .reset_index()
    )

    # Join med intervals with polypharmacy window per patient
    merged = meds.merge(poly_ranges, on="PATIENT", how="inner")

    # Keep meds overlapping with patient's polypharmacy interval
    merged = merged[
        (merged["STOP"] >= merged["poly_start"]) &
        (merged["START"] <= merged["poly_end"])
    ]

    if merged.empty:
        return pd.DataFrame(columns=["pair", "count"])

    # Use medication CODE or DESCRIPTION as unique ID
    merged["med_id"] = merged["CODE"].fillna(merged["DESCRIPTION"]).astype(str)

    # Build co-occurrence pairs per patient (interval overlap based)
    pairs = []

    for pid, grp in merged.groupby("PATIENT"):
        # Sort by interval start
        grp_sorted = grp.sort_values("START")
        meds_list = grp_sorted[["med_id", "START", "STOP"]].values

        # Compare intervals for overlap
        for i in range(len(meds_list)):
            med_a, start_a, stop_a = meds_list[i]
            for j in range(i + 1, len(meds_list)):
                med_b, start_b, stop_b = meds_list[j]

                # If intervals do NOT overlap, break early
                if start_b > stop_a:
                    break

                # Overlapping -> record the pair
                pairs.append(tuple(sorted((med_a, med_b))))

    if not pairs:
        return pd.DataFrame(columns=["pair", "count"])

    # Count pairs
    df_pairs = pd.DataFrame(pairs, columns=["med_a", "med_b"])
    df_pairs["pair"] = df_pairs["med_a"] + " + " + df_pairs["med_b"]

    return (
        df_pairs.groupby("pair")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

# ================================
# 9. Categorize duration into bands
# ================================
def categorize_duration(days: int) -> str:
    if days <= 7:
        return "0-7 days"
    elif days <= 30:
        return "8-30 days"
    elif days <= 90:
        return "31-90 days"
    elif days <= 180:
        return "91-180 days"
    else:
        return "180+ days"

@st.cache_data(show_spinner=False)
def get_poly_by_class(medications, poly_days, med_class_map):
    """
    Computes therapeutic class contribution to polypharmacy exposure.
    """

    if medications.empty or poly_days.empty:
        return pd.DataFrame()

    meds = medications.copy()
    meds["START"] = pd.to_datetime(meds["START"]).dt.normalize()
    meds["STOP"] = pd.to_datetime(meds["STOP"]).fillna(meds["START"]).dt.normalize()

    poly_ranges = (
        poly_days.groupby("PATIENT")
        .agg(poly_start=("day", "min"), poly_end=("day", "max"))
        .reset_index()
    )

    merged = meds.merge(poly_ranges, on="PATIENT", how="inner")

    mask = (
        (merged["STOP"] >= merged["poly_start"]) &
        (merged["START"] <= merged["poly_end"])
    )
    overlapped = merged[mask]

    if overlapped.empty:
        return pd.DataFrame()

    # Classify into therapeutic classes
    overlapped["class"] = overlapped.apply(
        lambda r: classify_medication(r["DESCRIPTION"], r["CODE"], med_class_map),
        axis=1
    )

    by_class = (
        overlapped.groupby("class")["PATIENT"]
        .nunique()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    return by_class
