
import pandas as pd
import pickle

cat_cols = ["Occupancy", "Construction_Type", "Industry_Type",
            "Sprinkler_System", "Fire_Hydrant_Onsite", "Requested_Coverage"]

num_cols = ["Building_Age_Years", "Sum_Insured_INR", "Number_of_Employees",
            "Years_in_Business", "Prior_Claims_Count", "Deductible_INR"]

def preprocess_submission(df):
    """
    Call this on any new live submission from Student 4.
    Loads the saved encoder and scaler -- never re-fits them.
    Input:  raw dataframe with original column names
    Output: cleaned, encoded, scaled dataframe ready for models
    """
    df = df.copy()

    # Fill missing values
    for col in cat_cols:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown")
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())

    # Load the saved encoder and scaler
    with open("encoder.pkl", "rb") as f:
        encoder = pickle.load(f)
    with open("scaler.pkl", "rb") as f:
        scaler = pickle.load(f)

    # Encode categorical columns
    cols_to_encode = [c for c in cat_cols if c in df.columns]
    encoded_array = encoder.transform(df[cols_to_encode])
    encoded_df = pd.DataFrame(
        encoded_array,
        columns=encoder.get_feature_names_out(cols_to_encode),
        index=df.index
    )
    df = df.drop(columns=cols_to_encode)
    df = pd.concat([df, encoded_df], axis=1)

    # Scale numeric columns
    cols_to_scale = [c for c in num_cols if c in df.columns]
    df[cols_to_scale] = scaler.transform(df[cols_to_scale])

    return df
