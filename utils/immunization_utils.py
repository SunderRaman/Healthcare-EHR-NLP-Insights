import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px


MONTH_NAMES = {
    1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",
    7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"
}

# ---------------------------------------------------------
# AGE BAND HELPER (reuse across project)
# ---------------------------------------------------------
def get_age_band(age):
    if pd.isna(age):
        return "Unknown"
    age = int(age)
    if age < 2:  return "0-1"
    if age < 13: return "2-12"
    if age < 20: return "13-19"
    if age < 50: return "20-49"
    if age < 65: return "50-64"
    return "65+"


# ---------------------------------------------------------
# 1. PREPROCESS IMMUNIZATIONS
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def preprocess_immunizations(immun_df, patients_df):
    """
    Returns:
      df: cleaned immunization dataframe with:
          DATE, PATIENT, CODE, DESCRIPTION, BASE_COST, age, age_band
    """
    df = immun_df.copy()

    # merge patient age
    df = df.merge(
        patients_df[["id", "age"]].rename(columns={"id": "PATIENT"}),
        on="PATIENT",
        how="left"
    )

    df["age_band"] = df["age"].apply(get_age_band)
    df["DATE"] = pd.to_datetime(df["DATE"])

    return df


# ---------------------------------------------------------
# 2. VACCINATIONS OVER TIME
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def immunization_time_series(df):
    ts = (
        df.groupby(df["DATE"].dt.to_period("M"))["PATIENT"]
        .count()
        .reset_index(name="count")
    )
    ts["DATE"] = ts["DATE"].astype(str)
    return ts


# ---------------------------------------------------------
# 3. MOST COMMON VACCINES
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def vaccine_rank(df):
    return (
        df.groupby("DESCRIPTION")["PATIENT"]
        .count()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )


# ---------------------------------------------------------
# 4. AGE GROUP COVERAGE
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def age_group_coverage(df, patients_df):

    vaccinated = (
        df.groupby("age_band")["PATIENT"]
        .nunique()
        .reset_index(name="vaccinated")
    )

    cohort = (
        patients_df.assign(age_band=lambda x: x["age"].apply(get_age_band))
        .groupby("age_band")["id"]
        .nunique()
        .reset_index(name="cohort")
    )

    return vaccinated.merge(cohort, on="age_band", how="left")


# ---------------------------------------------------------
# 5. VACCINE x AGE HEATMAP
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def vaccine_age_heatmap(df):
    heat = (
        df.groupby(["DESCRIPTION", "age_band"])["PATIENT"]
        .nunique()
        .reset_index(name="count")
    )
    pivot = heat.pivot_table(
        index="DESCRIPTION",
        columns="age_band",
        values="count",
        fill_value=0
    )
    return pivot


# ---------------------------------------------------------
# 6. BUILD PLOTLY FIGURES (OPTIONAL HELPERS)
# ---------------------------------------------------------
def fig_top_vaccines(df_top):
    fig = px.bar(
        df_top.head(20),
        x="DESCRIPTION",
        y="count",
        title="Most Common Vaccines",
    )
    fig.update_layout(xaxis_tickangle=-45)
    return fig


def fig_time_series(ts):
    return px.line(
        ts, x="DATE", y="count",
        title="Immunizations Over Time",
        markers=True
    )


def fig_age_coverage(cov):
    fig = px.bar(
        cov,
        x="age_band",
        y="pct",
        title="Vaccination Coverage (%) by Age Group",
        labels={"pct": "Coverage %"}
    )
    return fig


def fig_heatmap(pivot):
    fig = px.imshow(
        pivot,
        text_auto=True,
        aspect="auto",
        title="Vaccine × Age Group Heatmap"
    )
    return fig

# ------Insights Generation --------
def generate_immunization_insights(df, top_vax, by_age, seasonality):
    insights = []

    # -----------------------------
    # 1. TOP VACCINES (UTILIZATION)
    # -----------------------------
    if not top_vax.empty:
        total = top_vax["count"].sum()
        top_row = top_vax.iloc[0]
        pct = (top_row["count"] / total) * 100

        insights.append({
            "domain": "immunizations",
            "severity": "medium",
            "signal": "top_vaccine",
            "message": (
                f"{top_row['DESCRIPTION']} is the most frequently administered vaccine, "
                f"accounting for {pct:.1f}% of all immunization events."
            )
        })

        top3 = top_vax.head(3)["DESCRIPTION"].tolist()
        insights.append({
            "domain": "immunizations",
            "severity": "medium",
            "signal": "top_3_vaccines",
            "message": (
                f"The top 3 vaccines by utilization are: {top3[0]}, {top3[1]}, and {top3[2]}, "
                f"showing where most vaccine demand is concentrated."
            )
        })

    # -----------------------------
    # 2. AGE GROUP INSIGHTS
    # -----------------------------
    if not by_age.empty:
        top_age = by_age.sort_values("count", ascending=False).iloc[0]
        low_age = by_age.sort_values("count", ascending=True).iloc[0]

        insights.append({
            "domain": "immunizations",
            "severity": "medium",
            "signal": "high_uptake_age_group",
            "message": (
                f"Patients aged {top_age['age_band']} receive the highest volume of immunizations "
                f"({top_age['count']} doses), indicating strong engagement or higher-dose schedules."
            )
        })

        insights.append({
            "domain": "immunizations",
            "severity": "medium",
            "signal": "low_uptake_age_group",
            "message": (
                f"Patients aged {low_age['age_band']} have the lowest vaccine uptake "
                f"({low_age['count']} doses), suggesting potential gaps in vaccination coverage."
            )
        })

    # -----------------------------
    # 3. SEASONALITY INSIGHTS
    # -----------------------------
    if not seasonality.empty:
        seasonality = seasonality.sort_values("count")
        low = seasonality.iloc[0]
        high = seasonality.iloc[-1]

        insights.append({
            "domain": "immunizations",
            "severity": "low",
            "signal": "seasonal_peak",
            "message": (
                f"Vaccination volume peaks in {MONTH_NAMES.get(high['month'], high['month'])}, "
                "likely aligning with seasonal vaccination campaigns."
            )
        })

        insights.append({
            "domain": "immunizations",
            "severity": "low",
            "signal": "seasonal_low",
            "message": (
                f"The lowest vaccination activity occurs in {MONTH_NAMES.get(low['month'], low['month'])}, "
                "possibly reflecting reduced clinic visits or low seasonal demand."
            )
        })

    # -----------------------------
    # 4. COST INSIGHTS
    # -----------------------------
    if "BASE_COST" in df.columns:
        cost_stats = df.groupby("DESCRIPTION")["BASE_COST"].mean().reset_index()
        high_cost = cost_stats.sort_values("BASE_COST", ascending=False).iloc[0]

        insights.append({
            "domain": "immunizations",
            "severity": "high",
            "signal": "high_cost_vaccine",
            "message": (
                f"{high_cost['DESCRIPTION']} has the highest average cost per dose "
                f"(${high_cost['BASE_COST']:.2f}), making it a key cost driver in your immunization program."
            )
        })

    # -----------------------------
    # 5. DOSE BURDEN PER PATIENT
    # -----------------------------
    doses_per_patient = df["PATIENT"].value_counts().mean()
    insights.append({
        "domain": "immunizations",
        "severity": "low",
        "signal": "dose_burden",
        "message": (
            f"On average, each vaccinated patient receives {doses_per_patient:.1f} doses."
        )
    })

    # ----------------------------------------------------------
    # ADVANCED (1): SPIKE / DROP DETECTION
    # ----------------------------------------------------------
    if not seasonality.empty and seasonality["count"].sum() > 0:
        seasonality_sorted = seasonality.sort_values("month")
        seasonality_sorted["pct_change"] = seasonality_sorted["count"].pct_change() * 100

        spikes = seasonality_sorted.sort_values("pct_change", ascending=False)
        if spikes.iloc[0]["pct_change"] > 20:
            m = spikes.iloc[0]
            insights.append({
                "domain": "immunizations",
                "severity": "high",
                "signal": "demand_spike",
                "message": (
                    f"A significant month-on-month increase ({m['pct_change']:.1f}%) "
                    f"was observed in {MONTH_NAMES[m['month']]}, indicating sudden demand growth."
                )
            })

        drops = seasonality_sorted.sort_values("pct_change", ascending=True)
        if drops.iloc[0]["pct_change"] < -20:
            m = drops.iloc[0]
            insights.append({
                "domain": "immunizations",
                "severity": "high",
                "signal": "demand_drop",
                "message": (
                    f"A sharp decline ({m['pct_change']:.1f}%) occurred in {MONTH_NAMES[m['month']]}, "
                    "which may indicate supply disruptions or reduced clinic attendance."
                )
            })

    # ----------------------------------------------------------
    # ADVANCED (2): POTENTIAL SCHEDULE ISSUES
    # ----------------------------------------------------------
    dose_counts = df.groupby(["PATIENT", "DESCRIPTION"]).size().reset_index(name="n")
    suspicious = dose_counts[dose_counts["n"] > 5]

    if not suspicious.empty:
        insights.append({
            "domain": "immunizations",
            "severity": "high",
            "signal": "repeat_doses",
            "message": (
                f"{len(suspicious)} patients received unusually high repeat doses of the same vaccine. "
                "This may indicate data entry duplication or irregular vaccination patterns."
            )
        })

    # ----------------------------------------------------------
    # ADVANCED (3): COST–VOLUME IMPACT
    # ----------------------------------------------------------
    if "BASE_COST" in df.columns:
        volume = df["DESCRIPTION"].value_counts().reset_index()
        volume.columns = ["DESCRIPTION", "count"]

        cost = df.groupby("DESCRIPTION")["BASE_COST"].mean().reset_index()
        merged = volume.merge(cost, on="DESCRIPTION", how="left")
        merged["impact"] = merged["count"] * merged["BASE_COST"]

        top_impact = merged.sort_values("impact", ascending=False).iloc[0]

        insights.append({
            "domain": "immunizations",
            "severity": "high",
            "signal": "financial_impact",
            "message": (
                f"{top_impact['DESCRIPTION']} has the highest financial impact "
                f"(${top_impact['impact']:.2f} total), making it a key candidate for "
                "cost-saving interventions."
            )
        })

    return insights



