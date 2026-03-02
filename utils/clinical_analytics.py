import pandas as pd

def compute_condition_statistics(conditions_df, patients_df):
    stats = {}

    # Top conditions by frequency
    top_conditions = (
        conditions_df["DESCRIPTION"]
        .value_counts()
        .head(10)
        .to_dict()
    )
    stats["top_conditions"] = top_conditions

    # Multimorbidity: number of distinct conditions per patient
    cond_counts = (
        conditions_df.groupby("PATIENT")["DESCRIPTION"]
        .nunique()
        .reset_index(name="condition_count")
    )

    stats["multimorbidity_distribution"] = (
        cond_counts["condition_count"]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    # Merge with age for age-based prevalence
    merged = cond_counts.merge(
        patients_df[["id", "age"]], 
        left_on="PATIENT", 
        right_on="id",
        how="left"
    )

    merged["age_group"] = pd.cut(
        merged["age"],
        bins=[0, 18, 44, 64, 200],
        labels=["0-18", "19-44", "45-64", "65+"]
    )

    stats["age_condition_distribution"] = (
        merged.groupby("age_group")["condition_count"]
        .mean()
        .round(2)
        .to_dict()
    )

    return stats


def compute_medication_statistics(medications_df):
    stats = {}

    # Polypharmacy using Option-A → unique medication names
    med_counts = (
        medications_df.groupby("PATIENT")["DESCRIPTION"]
        .nunique()
        .reset_index(name="med_count")
    )

    stats["polypharmacy_rate"] = round(
        (med_counts["med_count"] >= 5).mean() * 100, 2
    )

    stats["medication_distribution"] = (
        med_counts["med_count"]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    return stats


def compute_procedure_statistics(procedures_df):
    stats = {}

    stats["top_procedures"] = (
        procedures_df["description"]
        .value_counts()
        .head(10)
        .to_dict()
    )

    return stats


def compute_immunization_statistics(immunizations_df, patients_df):
    stats = {}

    imm_counts = immunizations_df.groupby("PATIENT").size()

    stats["immunization_rate"] = round(
        (imm_counts > 0).mean() * 100, 2
    )

    return stats


def compute_observation_statistics(observations_df):
    stats = {}

    # Most recorded observation types
    stats["top_observations"] = (
        observations_df["DESCRIPTION"]
        .value_counts()
        .head(10)
        .to_dict()
    )

    return stats

def compute_procedure_features(procedures):
    """
    Generates AI-ready features from procedure data
    """

    # ---------------------------------------
    # Patient-level aggregation
    # ---------------------------------------
    patient_features = (
        procedures
        .groupby("patient")
        .agg(
            procedure_count=("description", "count"),
            total_cost=("base_cost", "sum"),
            avg_cost=("base_cost", "mean"),
            first_procedure=("start", "min"),
            last_procedure=("start", "max")
        )
        .reset_index()
    )

    patient_features["active_days"] = (
        patient_features["last_procedure"] -
        patient_features["first_procedure"]
    ).dt.days + 1

    patient_features["procedures_per_day"] = (
        patient_features["procedure_count"] /
        patient_features["active_days"].replace(0, 1)
    )

    # ---------------------------------------
    # Outlier detection (z-score)
    # ---------------------------------------
    patient_features["z_proc_count"] = (
        (patient_features["procedure_count"] -
         patient_features["procedure_count"].mean()) /
        patient_features["procedure_count"].std()
    )

    patient_features["z_total_cost"] = (
        (patient_features["total_cost"] -
         patient_features["total_cost"].mean()) /
        patient_features["total_cost"].std()
    )

    return patient_features

def generate_rule_based_insights(patient_features):
    insights = []

    high_util = patient_features[patient_features["z_proc_count"] > 2]
    if not high_util.empty:
        insights.append({
            "domain": "procedures",
            "signal": "high_utilization",
            "severity": "high",
            "value": len(high_util),
            "message": f"{len(high_util)} patients have unusually high procedure utilization (>2σ above average)."
        })

    high_cost = patient_features[patient_features["z_total_cost"] > 2]
    if not high_cost.empty:
        insights.append({
            "domain": "procedures",
            "signal": "high_cost",
            "severity": "high",
            "value": len(high_cost),
            "message": f"{len(high_cost)} patients incur exceptionally high total procedure costs."
        })

    return insights

