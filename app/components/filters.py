import streamlit as st

def render_global_filters(patients, encounters, read_only=False):

    with st.sidebar:
        st.header("Global Filters")

        # Canonical values in session_state (used across pages)
        gender_value = st.session_state.get("gender_filter", "All")
        age_value = st.session_state.get("age_range", (0, 120))  # or (0, 100)
        encounter_types_all = sorted(encounters["encounter_class"].unique())
        encounter_value = st.session_state.get(
            "selected_encounter_types",
            encounter_types_all
        )

        if read_only:
            # --- READ-ONLY MODE: show current values, no keys, disabled ---
            st.selectbox(
                "Gender",
                ["All", "M", "F"],
                index=["All", "M", "F"].index(gender_value),
                disabled=True,
            )

            st.slider(
                "Age Range",
                0, 120,
                value=age_value,
                disabled=True,
            )

            st.multiselect(
                "Encounter Types",
                options=encounter_types_all,
                default=encounter_value,
                disabled=True,
            )

            # Return canonical values
            return gender_value, age_value, encounter_value

        # --- ACTIVE MODE (main page only) ---

        # Widgets use different keys (_widget) so we can manage the
        # canonical values ourselves without conflicts
        gender_widget = st.selectbox(
            "Gender",
            ["All", "M", "F"],
            index=["All", "M", "F"].index(gender_value),
            key="gender_filter_widget",
        )

        age_widget = st.slider(
            "Age Range",
            0, 120,
            value=age_value,
            key="age_range_widget",
        )

        selected_encounter_types_widget = st.multiselect(
            "Encounter Types",
            options=encounter_types_all,
            default=encounter_value,
            key="selected_encounter_types_widget",
        )

        # 🔑 Now we safely sync to canonical session_state keys
        st.session_state.gender_filter = gender_widget
        st.session_state.age_range = age_widget
        st.session_state.selected_encounter_types = selected_encounter_types_widget

        return gender_widget, age_widget, selected_encounter_types_widget
