# save as postprocess_med_to_class.py and run in same folder as med_to_class_final.csv
import pandas as pd
import re
from pathlib import Path

DATA_PATH = Path("data")

INPUT = Path(DATA_PATH/"med_to_class_final.csv")
OUTPUT = Path(DATA_PATH/"med_to_class_final_clean.csv")

df = pd.read_csv(INPUT, dtype=str).fillna("")

# normalize description lowercase for matching
df["DESCRIPTION_CLEAN"] = df["DESCRIPTION"].str.lower().str.replace(r"[^a-z0-9\s]", " ", regex=True)
df["ATC_METHOD"] = df.get("ATC_METHOD", "").astype(str)

# --------------------------
# Fallback ATC rules (balanced: mostly 2nd-level where useful)
# keys are substrings to search for in cleaned description
# Add or tweak entries if you spot mismatches.
# --------------------------
ATC_RULES = {
    # Antibiotics / antibacterials (J01)
    "nitrofurantoin": "J01XE01",
    "penicillin v": "J01CE02",
    "penicillin g": "J01CE03",
    "amoxicillin": "J01CA04",
    "ampicillin": "J01CA01",
    "cefuroxime": "J01DD02",
    "cefaclor": "J01DC04",
    "ciprofloxacin": "J01MA02",
    "piperacillin": "J01RA12",  # often combined with tazobactam
    "tazobactam": "J01RA12",
    "azithromycin": "J01FA10",
    "clindamycin": "J01FF01",
    "vancomycin": "J01XA01",
    "aztreonam": "J01DF01",
    "doxycycline": "J01AA02",
    "cef": "J01",  # generic fallback for cephalosporins

    # Analgesics / opioids / acute pain (N02)
    "oxycodone": "N02AA05",
    "hydrocodone": "N02AA05",
    "tramadol": "N02AX02",
    "fentanyl": "N02AB03",
    "meperidine": "N02AB02",
    "morphine": "N02AA01",
    "buprenorphine": "N02AE01",
    "sufentanil": "N01AH06",
    "tapentadol": "N02AX06",

    # NSAIDs (M01)
    "ibuprofen": "M01AE01",
    "naproxen": "M01AE02",
    "diclofenac": "M01AB05",

    # Antihistamines (R06)
    "cetirizine": "R06AE07",
    "levocetirizine": "R06AE09",
    "loratadine": "R06AX13",
    "fexofenadine": "R06AX26",
    "diphenhydramine": "R06AA02",
    "terfenadine": "R06AX05",

    # Decongestants / cough (R05)
    "dextromethorphan": "R05DA09",
    "guaifenesin": "R05CB03",

    # Cardiovascular (C)
    "warfarin": "B01AA03",  # anticoagulant (B01)
    "heparin": "B01AB01",
    "enoxaparin": "B01AB05",
    "aspirin": "B01AC06",
    "nitroglycerin": "C01DA02",
    "digoxin": "C01AA05",
    "verapamil": "C08DA01",  # calcium channel
    "carvedilol": "C07AG02",
    "furosemide": "C03CA01",

    # Respiratory inhalers (R03)
    "fluticasone": "R03BA02",  # corticosteroid inhaled (often combined)
    "salmeterol": "R03AC12",
    "albuterol": "R03AC02",
    "salbutamol": "R03AC02",
    "ipratropium": "R03AL01",

    # Gastro / PPI (A02)
    "omeprazole": "A02BC01",
    "pantoprazole": "A02BC02",
    "lansoprazole": "A02BC03",

    # Hormones / contraceptives (G03 / G02)
    "levonorgestrel": "G02BA03",
    "medroxyprogesterone": "G03DA02",
    "etonogestrel": "G03AC08",
    "norethindrone": "G03AC03",
    "ethinyl estradiol": "G03AA",
    "nuvaring": "G02BB01",
    "mirena": "G02BA03",
    "liletta": "G02BA03",
    "kyleena": "G02BA03",
    "yaz": "G03AA", "ortho tri": "G03AA", "norinyl": "G03AA",
    "jolivette": "G03AC", "camila": "G03AC", "errin": "G03AC",
    "seasonique": "G03AA",
    "levora": "G03AA",
    "estrostep": "G03AA",
    "norelg": "G03AA",  # partial substrings

    # Oncology / antineoplastics (L01)
    "oxaliplatin": "L01XA08",
    "cisplatin": "L01XA01",
    "paclitaxel": "L01CD01",
    "docetaxel": "L01CD02",
    "carboplatin": "L01XA02",
    "doxorubicin": "L01DB01",
    "epirubicin": "L01DB03",
    "trastuzumab": "L01XC03",
    "palbociclib": "L01EM10",
    "cisplatin": "L01XA01",
    "cyclophosphamide": "L01AA01",
    "cis": "L01",  # general

    # Immunology / biologics / anti-TNF etc
    "epoetin": "B03XA01",
    "epoetin alfa": "B03XA01",
    "dornase alfa": "R01",  # Pulmozyme - respiratory mucolytic (R05? but keep R)
    "trastuzumab": "L01XC03",

    # Neurology / Psych (N)
    "methylphenidate": "N06BA04",
    "diazepam": "N05BA01",
    "clonazepam": "N03AE01",
    "carbamazepine": "N03AF01",
    "duloxetine": "N06AX21",
    "milnacipran": "M01? (leave as N06?)",
    "galantamine": "N06DX03",
    "memantine": "N06DX01",
    "donepezil": "N06DA02",

    # Endocrine / anticancer adjuvants
    "anastrozole": "L02BG03",
    "tamoxifen": "L02BA01",

    # Misc common injectables / OR drugs
    "propofol": "N01AX10",
    "midazolam": "N05CD08",
    "rocuronium": "M03AC04",
    "isoflurane": "N01AB07",
    "remifentanil": "N01AB18",
    "sufentanil": "N01AH06",
    "atropine": "A03",  # misc; could be N07AG or A03
    "norepinephrine": "C01CA03",
    "epinephrine": "C01CA24",
    "vasopressin": "H01",  # often H01 hormone
    "heparin": "B01AB01",
    "enoxaparin": "B01AB05",

    # Antineoplastic targeted / kinase inhibitors
    "verzenio": "L01XE42",  # abemaciclib? verzenio is abemaciclib - adjust if needed
    "palbociclib": "L01EM10",

    # Anticoagulants / platelet
    "warfarin": "B01AA03",
    "clopidogrel": "B01AC04",

    # Vitamins & minerals
    "ferrous sulfate": "B03A", "vitamin b 12": "B03BA", "iron": "B03A",

    # Renal / diuretics
    "furosemide": "C03CA01", "spironolactone": "C03DA01",

    # Antibiotics (others)
    "ciprofloxacin": "J01MA02", "aztreonam": "J01DF08",

    # GI enzymes etc
    "pancreatin": "A09AA02",

    # COPD / asthma combined
    "fluticasone": "R03BA02", "salmeterol": "R03AC12",

    # Oncology supportive / chemo agents (some examples)
    "methotrexate": "L01BA01", "paclitaxel": "L01CD01",

    # Others where generic mapping suffices
    "tamoxifen": "L02BA01", "colchicine": "M04AC01", "allopurinol": "M04AA01",
    "aspirin": "B01AC06", "paracetamol": "N02BE01",
    "tramadol": "N02AX02", "oxycodone": "N02AA05",

    # Add common brand/strings as catch-alls
    "pulmozyme": "R03", "mirena": "G02BA03", "kyleena": "G02BA03", "liletta": "G02BA03",
    "nuvaring": "G02BB01", "etonogestrel": "G03AC08",
    "levonorgestrel": "G03AC", "etonogestrel": "G03AC",
    "levora": "G03AA", "yaz": "G03AA", "seasonique": "G03AA",
    "jolivette": "G03AC", "camila": "G03AC", "errin": "G03AC",
}

ATC_RULES.update({
    "phenazopyridine": "G04BX06",
    "leucovorin": "V03AF03",
    "natazia": "G03AB08",
    "trinessa": "G03AA12",
    "atomoxetine": "N06BA09",
    "chlorpheniramine": "R06AB04",
    "sodium chloride": "B05XA03",
    "hydrocortisone": "D07AA02",
    "alendronic": "M05BA04",
    "alendronate": "M05BA04",
    "alteplase": "B01AD02",
    "amiodarone": "C01BD01",
    "astemizole": "R06AX11",
    "leuprolide": "L02AE02",
    "captopril": "C09AA01",
    "fulvestrant": "L02BA03",
    "nicotine": "N07BA01",
    "mestranol": "G03AB03",
    "norethynodrel": "G03AB03",
    "sacubitril": "C09DX04",
    "valsartan": "C09CA03",
    "tacrine": "N06DA01",
    "cyclosporine": "L04AD01",
    "baricitinib": "L04AA37",
})
# --------------------------
# Mapping pass: apply fallback to rows with UNKNOWN ATC
# --------------------------
def apply_fallback_rules(row):
    atc = row.get("ATC_GROUP", "")
    if atc and atc != "UNKNOWN":
        return atc, row.get("ATC_METHOD", "")
    desc = row["DESCRIPTION_CLEAN"]
    # try rule keys (longer keys first)
    for key in sorted(ATC_RULES.keys(), key=lambda x: -len(x)):
        if key in desc:
            return ATC_RULES[key], f"fallback_rule:{key}"
    return "UNKNOWN", "unmapped"

# Apply to unknowns
idx_unknown = df[df["ATC_GROUP"].isna() | (df["ATC_GROUP"] == "") | (df["ATC_GROUP"] == "UNKNOWN")].index
for i in idx_unknown:
    new_atc, method = apply_fallback_rules(df.loc[i])
    df.at[i, "ATC_GROUP"] = new_atc
    # preserve existing ATC_METHOD if present (prefer via_code/name), else set
    if not df.at[i, "ATC_METHOD"]:
        df.at[i, "ATC_METHOD"] = method
    else:
        if df.at[i, "ATC_METHOD"] in ("", "unmapped"):
            df.at[i, "ATC_METHOD"] = method

# final safety: if any still UNKNOWN, mark as 'OTHER' (very rare)
df.loc[df["ATC_GROUP"].isna(), "ATC_GROUP"] = "UNKNOWN"
remaining_unknown = df[df["ATC_GROUP"] == "UNKNOWN"].shape[0]

# --------------------------
# CHRONIC_FLAG derivation from ATC (Option-C rules)
# use prefixes or 2-/3-level decisions
# --------------------------
def classify_by_atc(atc):
    atc = (atc or "").upper()
    if atc == "" or atc == "UNKNOWN":
        return "acute"  # conservative default
    # check for specific chronic groups (2nd-level or patterns)
    if atc.startswith(("A10","C03","C07","C08","C09","C10","N03","N05","N06","H03","B03","M05","G02","G03","R03","L04")):
        return "chronic"
    # chemotherapy (L01) is treated as acute (patient-level often episodic)
    if atc.startswith("L01"):
        return "acute"
    # Antibacterials, analgesics, NSAIDs, anticoagulants, many injectables => acute
    if atc.startswith(("J01","M01","N02","H02","A04","R05","C01","B01","N01")):
        return "acute"
    # others default acute
    return "acute"

df["CHRONIC_FLAG"] = df["ATC_GROUP"].apply(classify_by_atc)

# --------------------------
# Save final CSV
# --------------------------
df_out = df.drop(columns=["DESCRIPTION_CLEAN"])
df_out.to_csv(OUTPUT, index=False)

# --------------------------
# Summary printout
# --------------------------
total = len(df_out)
by_method = df_out["ATC_METHOD"].value_counts().to_dict()
unknown_after = (df_out["ATC_GROUP"] == "UNKNOWN").sum()
mapped_now = total - unknown_after

print("Finished mapping.")
print(f"Total rows: {total}")
print(f"Mapped rows (non-UNKNOWN): {mapped_now}")
print(f"Remaining UNKNOWN: {unknown_after}")
print("Mapping by method (top):")
for k, v in sorted(by_method.items(), key=lambda x: -x[1])[:20]:
    print(f"  {k}: {v}")

print(f"Output saved to: {OUTPUT}")
