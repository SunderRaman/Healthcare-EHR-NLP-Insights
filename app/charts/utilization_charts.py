import plotly.express as px

def encounter_volume_over_time(df):
    grouped = df.groupby(df["date"].dt.to_period("M")).size().reset_index(name="count")
    grouped["date"] = grouped["date"].dt.to_timestamp()

    fig = px.line(
        grouped,
        x="date",
        y="count",
        title="Encounter Volume Over Time",
        markers=True
    )
    return fig


def encounter_type_distribution(df):
    grouped = df["encounter_class"].value_counts().reset_index()
    grouped.columns = ["Encounter Type", "Count"]

    fig = px.bar(
        grouped,
        x="Encounter Type",
        y="Count",
        title="Encounter Type Distribution"
    )
    return fig


def age_distribution(df):
    fig = px.histogram(
        df,
        x="age",
        nbins=20,
        title="Patient Age Distribution"
    )
    return fig


def gender_distribution(df):
    grouped = df["gender"].value_counts().reset_index()
    grouped.columns = ["Gender", "Count"]

    fig = px.pie(
        grouped,
        names="Gender",
        values="Count",
        title="Gender Breakdown",
        hole=0.4
    )
    return fig
