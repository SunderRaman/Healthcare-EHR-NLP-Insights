def bucket_insights_by_severity(insights):
    buckets = {
        "high": [],
        "medium": [],
        "low": []
    }

    for ins in insights:
        sev = ins.get("severity", "low")
        buckets.setdefault(sev, []).append(ins)

    return buckets