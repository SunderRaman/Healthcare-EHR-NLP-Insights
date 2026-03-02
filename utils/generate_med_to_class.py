import pandas as pd
import re
from pathlib import Path

DATA_PATH = Path("data")
# -------------------------------------------------------
# Load unique meds file
# -------------------------------------------------------
df = pd.read_csv(DATA_PATH/"unique_medications_for_mapping.csv")
df["DESCRIPTION"] = df["DESCRIPTION"].astype(str).str.strip().str.lower()

# -------------------------------------------------------
# 1. Extract ingredient keyword (first word or cleaned)
# -------------------------------------------------------
def extract_ingredient(desc):
    # remove strength like "500 mg", "5 MG", etc.
    text = re.sub(r"\b\d+(\.\d+)?\s*(mg|mcg|g|ml)\b", "", desc)
    # remove NDA codes or packaging info
    text = re.sub(r"[^\w\s]", " ", text)
    text = text.strip()
    # take first meaningful word
    tokens = text.split()
    return tokens[0] if tokens else desc

df["ingredient"] = df["DESCRIPTION"].apply(extract_ingredient)

# -------------------------------------------------------
# 2. Map ingredient to ATC therapeutic group (Option-D)
# -------------------------------------------------------
ATC_RULES = {
    # Chronic meds
    "metformin": "A10",        # Diabetes
    "insulin": "A10",
    "atorvastatin": "C10",     # Lipid-lowering
    "simvastatin": "C10",
    "pravastatin": "C10",
    "lisinopril": "C09",       # ACE inhibitors
    "amlodipine": "C08",       # Calcium channel blockers
    "losartan": "C09",         # ARBs
    "hydrochlorothiazide": "C03",
    "levothyroxine": "H03",
    "sertraline": "N06",
    "fluoxetine": "N06",
    "gabapentin": "N03",
    "metoprolol": "C07",
    "clopidogrel": "B01",
    "warfarin": "B01",

    # Acute meds
    "ibuprofen": "M01",
    "acetaminophen": "N02",
    "paracetamol": "N02",
    "amoxicillin": "J01",
    "azithromycin": "J01",
    "dextromethorphan": "R05",
    "epinephrine": "C01",
    "prednisone": "H02",
    "prednisolone": "H02",
    "naproxen": "M01",
    "ondansetron": "A04",
}

def map_atc(ingredient):
    for key in ATC_RULES:
        if key in ingredient:
            return ATC_RULES[key]
    return "UNKNOWN"

df["ATC_GROUP"] = df["ingredient"].apply(map_atc)

# -------------------------------------------------------
# 3. ATC → Chronic/Acute classification
# -------------------------------------------------------
def classify_chronic(atc):
    if atc in ["A10", "C03", "C07", "C08", "C09", "C10", "N03", "N05", "N06", "H03", "B01"]:
        return "chronic"
    if atc in ["J01", "M01", "N02", "H02", "A04", "R05", "C01"]:
        return "acute"
    return "acute"  # default conservative

df["CHRONIC_FLAG"] = df["ATC_GROUP"].apply(classify_chronic)

# -------------------------------------------------------
# 4. Save final mapping
# -------------------------------------------------------
output = df[["CODE", "DESCRIPTION", "ATC_GROUP", "CHRONIC_FLAG"]]
output.to_csv(DATA_PATH/"med_to_class.csv", index=False)

print("\nGenerated med_to_class.csv successfully!")
print(output.head(20))
