
import pandas as pd
import numpy as np
import pickle
import statsmodels.api as sm
import importlib.util

UPLIFT_CAP = 0.40

def get_price_and_explanation(submission_dict):
    with open("freq_model.pkl",          "rb") as f: freq_model       = pickle.load(f)
    with open("sev_model.pkl",           "rb") as f: sev_model        = pickle.load(f)
    with open("xgb_model.pkl",           "rb") as f: xgb_model        = pickle.load(f)
    with open("shap_explainer.pkl",      "rb") as f: explainer        = pickle.load(f)
    with open("glm_feature_columns.pkl", "rb") as f: glm_feature_cols = pickle.load(f)

    spec   = importlib.util.spec_from_file_location(
                 "preprocess_submission", "preprocess_submission.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    preprocess_submission = module.preprocess_submission

    ml_input = {
        "Occupancy": submission_dict.get("occupancy_type") or "Warehouse",
        "Construction_Type": submission_dict.get("construction_type") or "Unknown",
        "Building_Age_Years": float(submission_dict.get("building_age") or 0),
        "Sum_Insured_INR": float(submission_dict.get("sum_insured") or 0),
        "Number_of_Employees": float(submission_dict.get("number_of_employees") or 0),
        "Prior_Claims_Count": float(submission_dict.get("prior_claims_count") or 0),
        "Deductible_INR": float(submission_dict.get("deductible") or 0),
        "Sprinkler_System": "Yes" if submission_dict.get("sprinkler_system") is True else "No",
        "Fire_Hydrant_Onsite": "Yes" if submission_dict.get("fire_protection") is True else "No",
        "Years_in_Business": float(submission_dict.get("years_in_business") or 0),
        "Industry_Type": submission_dict.get("business_use") or "General"
    }

    df_input = pd.DataFrame([ml_input])
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
