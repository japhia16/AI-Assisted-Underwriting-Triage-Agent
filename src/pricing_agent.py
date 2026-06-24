
import pandas as pd
import numpy as np
import os
import pickle
import statsmodels.api as sm
import importlib.util
from src.preprocess_submission import normalize_requested_coverage

UPLIFT_CAP = 0.40

SRC_DIR = os.path.dirname(os.path.abspath(__file__))

def get_price_and_explanation(submission_dict):
    def load_pickle(name):
        path = os.path.join(SRC_DIR, name)
        with open(path, "rb") as f:
            return pickle.load(f)

    freq_model       = load_pickle("freq_model.pkl")
    sev_model        = load_pickle("sev_model.pkl")
    xgb_model        = load_pickle("xgb_model.pkl")
    explainer        = load_pickle("shap_explainer.pkl")
    glm_feature_cols = load_pickle("glm_feature_columns.pkl")

    spec   = importlib.util.spec_from_file_location(
                 "preprocess_submission", os.path.join(SRC_DIR, "preprocess_submission.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    preprocess_submission = module.preprocess_submission

    # Convert occupancy_type from int back to string if needed (price_endpoint converts it to int)
    occupancy_value = submission_dict.get("occupancy_type")
    if isinstance(occupancy_value, int):
        occupancy_value = {
            0: "Warehouse",
            1: "Office",
            2: "Retail",
            3: "Manufacturing",
            4: "Restaurant",
            5: "Hospitality",
            6: "Unknown",
        }.get(occupancy_value, "Unknown")
    else:
        occupancy_value = occupancy_value or "Warehouse"

    # Convert construction_type from int back to string if needed (price_endpoint converts it to int)
    construction_value = submission_dict.get("construction_type")
    if isinstance(construction_value, int):
        construction_value = {
            0: "Frame",
            1: "Joisted Masonry",
            2: "Non-Combustible",
            3: "Masonry Non-Combustible",
            4: "Modified Fire Resistive",
            5: "Fire Resistive (ISO Class 6)",
            6: "Unknown",
        }.get(construction_value, "Unknown")
    else:
        construction_value = construction_value or "Unknown"

    # MAP: NLP Extraction keys (from intake_agent) -> ML Model column names (Student 3 trained with these)
    ml_input = {
        "Occupancy": occupancy_value,
        "Construction_Type": construction_value,
        "Industry_Type": submission_dict.get("business_use", "General"),
        "Building_Age_Years": float(submission_dict.get("building_age", 0)),
        "Sum_Insured_INR": float(submission_dict.get("sum_insured", 1000000)),
        "Number_of_Employees": float(submission_dict.get("number_of_employees", 10)),
        "Years_in_Business": float(submission_dict.get("years_in_business", 5)),
        "Prior_Claims_Count": float(submission_dict.get("prior_claims_count", 0)),
        "Deductible_INR": float(submission_dict.get("deductible", 50000)),
        "Sprinkler_System": "Yes" if submission_dict.get("sprinkler_system") else "No",
        "Fire_Hydrant_Onsite": "Yes" if submission_dict.get("fire_protection") else "No",
        "Requested_Coverage": submission_dict.get("requested_coverage", "Standard Fire & Special Perils")
    }

    # DEBUG: Confirm all columns exist before preprocessing
    print("ML INPUT COLUMNS:")
    print(list(ml_input.keys()))

    df_input = pd.DataFrame([ml_input])
    
    print("\nDATAFRAME COLUMNS:")
    print(df_input.columns.tolist())
    
    df_clean = preprocess_submission(df_input)

    # Align GLM columns
    df_glm = sm.add_constant(df_clean, has_constant="add")
    for col in glm_feature_cols:
        if col not in df_glm.columns:
            df_glm[col] = 0
    df_glm = df_glm[glm_feature_cols]

    freq_pred   = float(freq_model.predict(df_glm).iloc[0])
    sev_pred    = float(sev_model.predict(df_glm).iloc[0])
    glm_premium = freq_pred * sev_pred

    # Align XGBoost columns
    xgb_feature_cols = xgb_model.get_booster().feature_names
    for col in xgb_feature_cols:
        if col not in df_clean.columns:
            df_clean[col] = 0
    df_clean_xgb = df_clean[xgb_feature_cols]

    xgb_pred      = float(xgb_model.predict(df_clean_xgb)[0])
    uplift        = (xgb_pred - glm_premium) / glm_premium
    capped_uplift = float(np.clip(uplift, -UPLIFT_CAP, UPLIFT_CAP))
    final_premium = glm_premium * (1 + capped_uplift)

    shap_vals     = explainer.shap_values(df_clean_xgb)[0]
    feature_names = df_clean_xgb.columns.tolist()
    top_features  = sorted(
        zip(feature_names, shap_vals),
        key=lambda x: abs(x[1]),
        reverse=True
    )[:3]

    explanation = [
        {
            "feature":     name,
            "shap_impact": round(float(val), 4),
            "direction":   "increases premium" if val > 0 else "reduces premium"
        }
        for name, val in top_features
    ]

    return {
        "glm_baseline_INR":   round(glm_premium, 2),
        "xgb_prediction_INR": round(xgb_pred, 2),
        "uplift_pct":         round(capped_uplift * 100, 2),
        "final_premium_INR":  round(final_premium, 2),
        "top_shap_features":  explanation
    }
