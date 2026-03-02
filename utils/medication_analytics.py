def generate_medication_insights(
    patient_poly,
    by_age,
    by_class,
    chronic_vs_acute_df,
    top_meds

):
    insights = []

    # ------------------------------------------------
    # 1. HIGH POLYPHARMACY
    # ------------------------------------------------
    high_poly = patient_poly[patient_poly["max_concurrent"] >= 5]
    if not high_poly.empty:
        insights.append({
            "domain": "medications",
            "severity": "medium",
            "signal": "high_polypharmacy",
            "message": (
                f"{len(high_poly)} patients experience high polypharmacy "
                f"(≥5 concurrent medications)."
            )
        })

    # ------------------------------------------------
    # 2. EXTREME POLYPHARMACY
    # ------------------------------------------------
    extreme_poly = patient_poly[patient_poly["max_concurrent"] >= 10]
    if not extreme_poly.empty:
        insights.append({
            "domain": "medications",
            "severity": "high",
            "signal": "extreme_polypharmacy",
            "message": (
                f"{len(extreme_poly)} patients show extreme polypharmacy "
                f"(≥10 concurrent medications), posing elevated safety risk."
            )
        })

    # ------------------------------------------------
    # CHRONIC VS ACUTE DOMINANCE
    # ------------------------------------------------
    if not chronic_vs_acute_df.empty:
        chronic = chronic_vs_acute_df[
            chronic_vs_acute_df["class"] == "chronic"
        ]["unique_patients"].values

        acute = chronic_vs_acute_df[
            chronic_vs_acute_df["class"] == "acute"
        ]["unique_patients"].values

        if len(chronic) and len(acute) and chronic[0] > acute[0]:
            insights.append({
                "domain": "medications",
                "severity": "medium",
                "signal": "chronic_dominance",
                "message": (
                    "Chronic medications account for a larger share of polypharmacy exposure "
                    "than acute medications, indicating long-term treatment complexity."
                )
            })

    # ------------------------------------------------
    # 4. AGE GROUP SKEW
    # ------------------------------------------------
    if not by_age.empty:
        top_age = by_age.sort_values("poly_patients", ascending=False).iloc[0]

        insights.append({
            "domain": "medications",
            "severity": "medium",
            "signal": "age_skew",
            "message": (
                f"Patients aged {top_age['age_band']} account for the highest "
                f"polypharmacy burden ({top_age['poly_patients']} patients)."
            )
        })

    # ------------------------------------------------
    # 5. DRUG CLASS CONCENTRATION
    # ------------------------------------------------
    if not by_class.empty:
        top_class = by_class.iloc[0]
        pct = (top_class["count"] / by_class["count"].sum()) * 100

        if pct > 30:
            insights.append({
                "domain": "medications",
                "severity": "medium",
                "signal": "class_concentration",
                "message": (
                    f"{top_class['class']} medications account for {pct:.1f}% "
                    f"of polypharmacy exposure, indicating concentration risk."
                )
            })


    # ------------------------------------------------
    # TOP MEDICATION CONCENTRATION
    # ------------------------------------------------
    if top_meds is not None and not top_meds.empty:
        total = top_meds["patient_count"].sum()
        top3 = top_meds.head(3)

        if total > 0:
            pct = (top3["patient_count"].sum() / total) * 100

        if pct > 40:  # configurable threshold
            insights.append({
                "domain": "medications",
                "severity": "medium",
                "signal": "top_med_concentration",
                "message": (
                    f"The top 3 medications account for {pct:.1f}% of polypharmacy exposure, "
                    f"indicating concentration risk around specific drugs."
                )
            })

        # Optional: single dominant medication
        top1 = top3.iloc[0]
        insights.append({
            "domain": "medications",
            "severity": "low",
            "signal": "top_medication",
            "message": (
                f"{top1['DESCRIPTION']} is the most common medication involved in polypharmacy, "
                f"affecting {top1['patient_count']} patients."
            )
        })

    return insights