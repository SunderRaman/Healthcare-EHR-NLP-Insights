import pandas as pd
import streamlit as st
import os

# Default path for the medication classification file
DEFAULT_MAPPING_FILE = "data/med_to_class_final_clean.csv"


@st.cache_data(show_spinner=False)
def load_med_class_map(filepath: str = DEFAULT_MAPPING_FILE) -> pd.DataFrame:
    """
    Loads the medication → ATC class mapping file.
    Ensures clean column names, validates required fields,
    and caches the DataFrame.

    Returns:
        pd.DataFrame with columns:
            CODE, DESCRIPTION, ATC_GROUP, CHRONIC_FLAG
    """
    if not os.path.exists(filepath):
        st.warning(f"Medication class mapping file not found: {filepath}")
        return pd.DataFrame(columns=["CODE", "DESCRIPTION", "ATC_GROUP", "CHRONIC_FLAG"])

    try:
        df = pd.read_csv(filepath)

        # Normalize columns
        df.columns = df.columns.str.strip().str.upper()

        # Validate required columns
        required_cols = {"CODE", "DESCRIPTION", "ATC_GROUP", "CHRONIC_FLAG"}
        missing = required_cols - set(df.columns)

        if missing:
            st.error(f"Mapping file missing required columns: {missing}")
            return pd.DataFrame(columns=list(required_cols))

        # Cleanup
        df = df[list(required_cols)].copy()
        df = df.drop_duplicates(subset=["CODE"], keep="first")
        df["CODE"] = df["CODE"].astype(str).str.strip()

        # Normalize chronic_flag values
        df["CHRONIC_FLAG"] = (
            df["CHRONIC_FLAG"]
            .astype(str)
            .str.lower()
            .str.strip()
            .replace({"chronic": "chronic", "acute": "acute"})
        )

        return df

    except Exception as e:
        st.error(f"Error loading medication class map: {e}")
        return pd.DataFrame(columns=["CODE", "DESCRIPTION", "ATC_GROUP", "CHRONIC_FLAG"])
