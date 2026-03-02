import pandas as pd
from pathlib import Path

DATA_PATH = Path("data")

def load_patients():
    patients = pd.read_csv(DATA_PATH / "patients.csv")

    # Normalize all columns to lowercase FIRST
    patients.columns = patients.columns.str.lower()

    # Now 'gender' column exists in lowercase form
    patients["gender"] = patients["gender"].fillna("Unknown").str.title()

    # Compute age
    patients["birthdate"] = pd.to_datetime(patients["birthdate"], errors="coerce")
    patients["age"] = (pd.Timestamp.today() - patients["birthdate"]).dt.days // 365

    return patients



def load_encounters():
    encounters = pd.read_csv(DATA_PATH / "encounters.csv")

    # Normalize all columns to lowercase FIRST
    encounters.columns = encounters.columns.str.lower()

    # Standardize date field
    encounters["date"] = pd.to_datetime(encounters["start"], errors="coerce").dt.tz_localize(None)

    # Normalize encounter class (older datasets may not have this column)
    if "encounterclass" in encounters.columns:
        encounters["encounter_class"] = encounters["encounterclass"].fillna("Unknown").str.title()
    else:
        encounters["encounter_class"] = "Unknown"

    return encounters

def load_conditions():
    df = pd.read_csv(DATA_PATH / "conditions.csv")
    return df

def load_medications():
    df = pd.read_csv(DATA_PATH / "medications.csv")
    return df

def load_procedures():
    df = pd.read_csv(DATA_PATH / "procedures.csv")
    # Normalize column names
    df.columns = df.columns.str.lower()

    # Parse dates
    df["start"] = pd.to_datetime(df["start"], errors="coerce").dt.tz_localize(None)
    df["stop"] = pd.to_datetime(df["stop"], errors="coerce").dt.tz_localize(None)

    return df

def load_immunizations():
    df = pd.read_csv(DATA_PATH /  "immunizations.csv")
    return df

def load_observations():
    df = pd.read_csv(DATA_PATH / "observations.csv")
    return df


