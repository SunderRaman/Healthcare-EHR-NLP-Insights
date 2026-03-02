import pandas as pd
from pathlib import Path

DATA_PATH = Path("data")

meds = pd.read_csv(DATA_PATH/"medications.csv")
unique_meds = meds[["CODE", "DESCRIPTION"]].drop_duplicates()

unique_meds.to_csv(DATA_PATH/"unique_medications_for_mapping.csv", index=False)