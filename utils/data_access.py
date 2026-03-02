import streamlit as st

def get_filtered_data():
    """
    Returns filtered datasets that were computed on the main page.
    Used by all dashboard pages.
    """

    required_keys = [
        "filtered_patients",
        "filtered_encounters",
        "filtered_conditions",
        "filtered_medications",
        "filtered_procedures",
        "filtered_immunizations",
        "filtered_observations",
    ]

    # safety guard
    for key in required_keys:
        if key not in st.session_state:
            st.error("Filters not initialized — please return to the Home page first.")
            st.stop()

    return (
        st.session_state.filtered_patients,
        st.session_state.filtered_encounters,
        st.session_state.filtered_conditions,
        st.session_state.filtered_medications,
        st.session_state.filtered_procedures,
        st.session_state.filtered_immunizations,
        st.session_state.filtered_observations,
    )