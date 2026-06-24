
import logging
import os
import pandas as pd
import pickle

logger = logging.getLogger(__name__)

COVERAGE_LABEL_MAP = {
    "fire and allied perils":           "Standard Fire & Special Perils",
    "standard fire and special perils": "Standard Fire & Special Perils",
    "property all risk":                "All Risk (Comprehensive)",
    "all risk":                         "All Risk (Comprehensive)",
    "comprehensive":                    "All Risk (Comprehensive)",
    "fire only":                        "Fire Only",
    "fire + burglary":                  "Fire + Burglary",
    "fire and burglary":                "Fire + Burglary",
}

cat_cols = ["Occupancy", "Construction_Type", "Industry_Type",
            "Sprinkler_System", "Fire_Hydrant_Onsite", "Requested_Coverage"]

num_cols = ["Building_Age_Years", "Sum_Insured_INR", "Number_of_Employees",
            "Years_in_Business", "Prior_Claims_Count", "Deductible_INR"]

def normalize_requested_coverage(value):
    if value is None:
        return "Standard Fire & Special Perils"
    if not isinstance(value, str):
        value = str(value)
    text = value.strip().lower()
    if text in COVERAGE_LABEL_MAP:
        return COVERAGE_LABEL_MAP[text]
    for key, normalized in COVERAGE_LABEL_MAP.items():
        if key in text:
            return normalized
    if text in ["unknown", "", "na", "n/a"]:
        return "Unknown"
    logger.warning(
        "Unknown requested coverage label %r; defaulting to Standard Fire & Special Perils",
        value,
    )
    return "Standard Fire & Special Perils"


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

    if "Requested_Coverage" in df.columns:
        df["Requested_Coverage"] = df["Requested_Coverage"].apply(normalize_requested_coverage)

    src_dir = os.path.dirname(os.path.abspath(__file__))
    # Load the saved encoder and scaler from src/ so the runtime path is deterministic
    with open(os.path.join(src_dir, "encoder.pkl"), "rb") as f:
        encoder = pickle.load(f)
    with open(os.path.join(src_dir, "scaler.pkl"), "rb") as f:
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
