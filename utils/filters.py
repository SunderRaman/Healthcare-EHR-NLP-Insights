import streamlit as st

def apply_global_filters(patients, encounters, conditions,
                         medications, procedures, immunizations, observations,
                         gender_filter, age_range, selected_encounter_types):

    # Step 1: Gender filter
    filtered_patients = patients
    if gender_filter != "All":
        filtered_patients = filtered_patients[
            filtered_patients["gender"] == gender_filter
        ]

    # Step 2: Age filter
    filtered_patients = filtered_patients[
        filtered_patients["age"].between(age_range[0], age_range[1])
    ]

    # Step 3: Encounter filter by type
    filtered_encounters = encounters[
        encounters["encounter_class"].isin(selected_encounter_types)
    ]

    # Step 4: Match encounters to filtered patients
    filtered_encounters = filtered_encounters[
        filtered_encounters["patient"].isin(filtered_patients["id"])
    ]

    # Step 5: Clinical datasets filtered to patient list
    patient_ids = filtered_patients["id"]

    filtered_conditions = conditions[conditions["PATIENT"].isin(patient_ids)].copy()
    filtered_medications = medications[medications["PATIENT"].isin(patient_ids)].copy()
    filtered_procedures = procedures[procedures["patient"].isin(patient_ids)].copy()
    filtered_immunizations = immunizations[immunizations["PATIENT"].isin(patient_ids)].copy()
    filtered_observations = observations[observations["PATIENT"].isin(patient_ids)].copy()

    return (
        filtered_patients,
        filtered_encounters,
        filtered_conditions,
        filtered_medications,
        filtered_procedures,
        filtered_immunizations,
        filtered_observations,
    )
