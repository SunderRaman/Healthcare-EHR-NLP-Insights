def collect_all_insights(
    procedure_insights=None,
    medication_insights=None,
    #condition_insights=None,
    #vital_insights=None,
    immunization_insights=None
):
    all_insights = []

    for group in [
        procedure_insights,
        medication_insights,
        #condition_insights,
        #vital_insights,
        immunization_insights
    ]:
        if group:
            all_insights.extend(group)

    return all_insights
