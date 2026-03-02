import pandas as pd

def compute_utilization_metrics(patients_df, encounters_df):
    metrics = {}

    # Total counts
    metrics["total_patients"] = len(patients_df)
    metrics["total_encounters"] = len(encounters_df)

    # Encounter type distribution
    metrics["top_encounter_type"] = (
        encounters_df["encounter_class"].value_counts().idxmax()
        if len(encounters_df) > 0 else None
    )

    # Gender utilization
    metrics["gender_distribution"] = (
        patients_df["gender"].value_counts(normalize=True).round(3).to_dict()
    )

    # Age cohort bands
    patients_df["age_group"] = pd.cut(
        patients_df["age"],
        bins=[0, 18, 44, 64, 200],
        labels=["0-18", "19-44", "45-64", "65+"]
    )

    metrics["age_distribution"] = (
        patients_df["age_group"].value_counts(normalize=True).round(3).to_dict()
    )

    # Time trend (month over month)
    if "date" in encounters_df.columns and len(encounters_df) > 1:
        monthly_counts = (
            encounters_df.groupby(encounters_df["date"].dt.to_period("M"))
            .size()
            .sort_index()
        )

        if len(monthly_counts) >= 2:
            latest = monthly_counts.iloc[-1]
            previous = monthly_counts.iloc[-2]
            metrics["trend_percent_change"] = round(((latest - previous) / previous) * 100, 2) if previous > 0 else None
        else:
            metrics["trend_percent_change"] = None
    else:
        metrics["trend_percent_change"] = None

    return metrics

