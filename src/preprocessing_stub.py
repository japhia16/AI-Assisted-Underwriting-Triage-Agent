import pandas as pd
import pickle
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)

def _find_file(filename):
    for folder in [BASE_DIR, PARENT_DIR]:
        path = os.path.join(folder, filename)
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        f"{filename} not found. Make sure it is in the src/ folder "
        f"or the root project folder. You need to get this file from Student 3."
    )

CAT_COLS = ["Occupancy", "Construction_Type", "Industry_Type", "Sprinkler_System", "Fire_Hydrant_Onsite", "Requested_Coverage"]
NUM_COLS = ["Building_Age_Years", "Sum_Insured_INR", "Number_of_Employees", "Years_in_Business", "Prior_Claims_Count", "Deductible_INR"]

def preprocess_submission(submission: dict) -> pd.DataFrame:
    encoder = pickle.load(open(_find_file("encoder.pkl"), "rb"))
    scaler  = pickle.load(open(_find_file("scaler.pkl"),  "rb"))

    df = pd.DataFrame([submission])

    for col in CAT_COLS:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown")
        else:
            df[col] = "Unknown"

    for col in NUM_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0

    cols_to_encode = [c for c in CAT_COLS if c in df.columns]
    encoded_array  = encoder.transform(df[cols_to_encode])
    encoded_df     = pd.DataFrame(encoded_array, columns=encoder.get_feature_names_out(cols_to_encode), index=df.index)
    
    df = df.drop(columns=cols_to_encode)
    df = pd.concat([df, encoded_df], axis=1)

    cols_to_scale = [c for c in NUM_COLS if c in df.columns]
    df[cols_to_scale] = scaler.transform(df[cols_to_scale])

    return df
