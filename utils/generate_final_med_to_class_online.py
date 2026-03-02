import pandas as pd
import requests
import re
import time
import sys
from pathlib import Path

DATA_PATH = Path("data")

INPUT_FILE = Path(DATA_PATH/"unique_medications_for_mapping.csv")
OUTPUT_FILE = Path(DATA_PATH/"med_to_class_final.csv")

df = pd.read_csv(INPUT_FILE, dtype=str)
df["DESCRIPTION"] = df["DESCRIPTION"].str.lower().str.strip()
df["CODE"] = df["CODE"].astype(str)

# -----------------------------------------------------------
# GLOBAL CACHES for SPEED
# -----------------------------------------------------------
RXCUI_CACHE = {}              # ingredient → rxcui
ATC_FROM_RCXUI_CACHE = {}     # rxcui → ATC
TERM_CACHE = {}               # description → extracted tokens

# -----------------------------------------------------------
# FAST PROGRESS BAR
# -----------------------------------------------------------
def print_progress(current, total, start_time):
    bar_len = 40
    frac = current / total
    filled = int(frac * bar_len)
    bar = "█" * filled + "-" * (bar_len - filled)

    elapsed = time.time() - start_time
    eta = (elapsed / current) * (total - current) if current > 0 else 0

    sys.stdout.write(
        f"\r |{bar}| {current}/{total} "
        f"({frac*100:5.1f}%)  Elapsed: {elapsed:5.1f}s  ETA: {eta:5.1f}s"
    )
    sys.stdout.flush()


# -----------------------------------------------------------
# 1️⃣ CLEAN TEXT + EXTRACT TERMS
# -----------------------------------------------------------
def extract_terms(description):
    """
    Extract 1-word, 2-word, 3-word ingredient-like tokens.
    Cached for speed.
    """
    if description in TERM_CACHE:
        return TERM_CACHE[description]

    desc = re.sub(r"[^\w\s]", " ", description)
    desc = re.sub(r"\s+", " ", desc).strip()
    tokens = desc.split()

    terms = []
    if len(tokens) >= 1:
        terms.append(tokens[0])
    if len(tokens) >= 2:
        terms.append(" ".join(tokens[:2]))
    if len(tokens) >= 3:
        terms.append(" ".join(tokens[:3]))

    TERM_CACHE[description] = terms
    return terms


# -----------------------------------------------------------
# 2️⃣ RXNORM LOOKUP (with caching + retry)
# -----------------------------------------------------------
def rxnorm_lookup_by_name(term):
    """
    Try to lookup ingredient using RxNorm (with cache + retry).
    """
    if term in RXCUI_CACHE:
        return RXCUI_CACHE[term]

    for attempt in range(3):  # retry up to 3 times
        try:
            # Exact match
            url_exact = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={term}"
            r = requests.get(url_exact, timeout=5).json()
            if "idGroup" in r and "rxnormId" in r["idGroup"]:
                rxcui = r["idGroup"]["rxnormId"][0]
                RXCUI_CACHE[term] = rxcui
                return rxcui

            # Approximate match (fallback)
            url_approx = f"https://rxnav.nlm.nih.gov/REST/approximateMatch.json?term={term}"
            r = requests.get(url_approx, timeout=5).json()

            if ("approximateGroup" in r and
                "candidate" in r["approximateGroup"]):
                rxcui = r["approximateGroup"]["candidate"][0]["rxcui"]
                RXCUI_CACHE[term] = rxcui
                return rxcui

        except:
            time.sleep(1)  # brief wait on failure

    RXCUI_CACHE[term] = None
    return None


# -----------------------------------------------------------
# 3️⃣ ATC lookup from RXCUI (with caching)
# -----------------------------------------------------------
def rxnorm_get_atc_from_rxcui(rxcui):
    if rxcui in ATC_FROM_RCXUI_CACHE:
        return ATC_FROM_RCXUI_CACHE[rxcui]

    for attempt in range(3):
        try:
            url = f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/property?propName=ATC"
            r = requests.get(url, timeout=5).json()

            if ("propConceptGroup" in r and
                "propConcept" in r["propConceptGroup"]):
                atc = r["propConceptGroup"]["propConcept"][0]["propValue"]
                ATC_FROM_RCXUI_CACHE[rxcui] = atc
                return atc

        except:
            time.sleep(0.05)

    ATC_FROM_RCXUI_CACHE[rxcui] = None
    return None


# -----------------------------------------------------------
# 4️⃣ ATC_RULES fallback (heuristics)
# -----------------------------------------------------------
ATC_RULES = {
    "metformin": "A10", "insulin": "A10", "glimepiride": "A10",
    "atorvastatin": "C10", "simvastatin": "C10", "rosuvastatin": "C10",
    "lisinopril": "C09", "amlodipine": "C08", "losartan": "C09",
    "hydrochlorothiazide": "C03",
    "levothyroxine": "H03",
    "sertraline": "N06", "fluoxetine": "N06",
    "gabapentin": "N03", "pregabalin": "N03",
    "metoprolol": "C07", "clopidogrel": "B01",

    # Acute meds
    "ibuprofen": "M01", "naproxen": "M01",
    "acetaminophen": "N02", "paracetamol": "N02",
    "amoxicillin": "J01", "azithromycin": "J01",
    "ondansetron": "A04", "prednisone": "H02",
    "dextromethorphan": "R05", "guaifenesin": "R05",
    "albuterol": "R03"
}


# -----------------------------------------------------------
# 5️⃣ MAIN BEST-ATC LOOKUP
# -----------------------------------------------------------
def get_best_atc(code, description):
    """
    Multi-stage ATC lookup:
    1️⃣ Try ATC directly from CODE (if CODE is an RXCUI)
    2️⃣ Try 1-word, 2-word, 3-word ingredient lookups
    3️⃣ Fallback rules
    """
    # Stage 1 — Code → ATC
    atc = rxnorm_get_atc_from_rxcui(code)
    if atc:
        return atc, "via_code"

    # Stage 2 — Name-based term matching
    for term in extract_terms(description):
        rxcui = rxnorm_lookup_by_name(term)
        if rxcui:
            atc = rxnorm_get_atc_from_rxcui(rxcui)
            if atc:
                return atc, f"via_name:{term}"

    # Stage 3 — Fallback
    for key in ATC_RULES:
        if key in description:
            return ATC_RULES[key], "fallback_rule"

    return "UNKNOWN", "unmapped"


# -----------------------------------------------------------
# 6️⃣ MAIN PROCESS LOOP
# -----------------------------------------------------------
print("\nStarting RxNorm → ATC mapping...\n")
start_time = time.time()

atc_list = []
method_list = []

for i, row in df.iterrows():
    atc, method = get_best_atc(row["CODE"], row["DESCRIPTION"])
    atc_list.append(atc)
    method_list.append(method)
    print_progress(i + 1, len(df), start_time)

print("\n\nATC mapping complete.\n")

df["ATC_GROUP"] = atc_list
df["ATC_METHOD"] = method_list


# -----------------------------------------------------------
# 7️⃣ Chronic/acute classification
# -----------------------------------------------------------
CHRONIC_ATC = ["A10","C03","C07","C08","C09","C10","N03","N05","N06","H03","B01","R03"]
ACUTE_ATC   = ["J01","M01","N02","H02","A04","R05","C01"]

def classify(atc):
    if atc in CHRONIC_ATC:
        return "chronic"
    if atc in ACUTE_ATC:
        return "acute"
    return "acute"   # default

df["CHRONIC_FLAG"] = df["ATC_GROUP"].apply(classify)


# -----------------------------------------------------------
# 8️⃣ SAVE OUTPUT
# -----------------------------------------------------------
df[["CODE", "DESCRIPTION", "ATC_GROUP", "CHRONIC_FLAG", "ATC_METHOD"]].to_csv(
    OUTPUT_FILE, index=False
)

print(f"Saved final file → {OUTPUT_FILE}\n")
print(df.head(10))
