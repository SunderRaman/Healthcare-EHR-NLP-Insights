from utils.load_data import load_patients, load_encounters
import pandas as pd

def run_verification():
    patients = load_patients()
    encounters = load_encounters()

    print("\n✅ Patients loaded:", len(patients))
    print("✅ Encounters loaded:", len(encounters))

    print("\nSample Patients:")
    print(patients.head())

    print("\nSample Encounters:")
    print(encounters.head())

if __name__ == "__main__":
    run_verification()
