import os
import json

# Ensure models are loaded from the src directory
os.chdir(os.path.dirname(__file__))

from pricing_agent import get_price_and_explanation


SAMPLE_SUBMISSION = {
    "Occupancy": "Warehouse",
    "Construction_Type": "Brick & Mortar",
    "Industry_Type": "Textiles & Garments",
    "Building_Age_Years": 25,
    "Sum_Insured_INR": 40000000,
    "Number_of_Employees": 120,
    "Years_in_Business": 10,
    "Prior_Claims_Count": 2,
    "Deductible_INR": 100000,
    "Sprinkler_System": "No",
    "Fire_Hydrant_Onsite": "Yes",
    "Requested_Coverage": "Standard Fire & Special Perils",
    "District": "Surat"
}


def pretty_print_quote(result: dict):
    print("\n=== COMMERCIAL PROPERTY INSURANCE QUOTE ===\n")
    print(f"GLM Baseline (INR):     {result['glm_baseline_INR']:,}")
    print(f"XGB Prediction (INR):   {result['xgb_prediction_INR']:,}")
    print(f"Applied Uplift (%):     {result['uplift_pct']}%")
    print(f"FINAL PREMIUM (INR):    {result['final_premium_INR']:,}\n")
    print("Top 3 SHAP drivers:")
    for i, feat in enumerate(result.get("top_shap_features", []), 1):
        print(f"  {i}. {feat['feature']}: {feat['shap_impact']} ({feat['direction']})")
    print("\nFull result (json):")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        print("Running end-to-end pricing pipeline...")
        res = get_price_and_explanation(SAMPLE_SUBMISSION)
        pretty_print_quote(res)
    except FileNotFoundError as e:
        print(f"ERROR: Missing model or preprocessing file: {e}")
    except Exception as e:
        print(f"ERROR running pipeline: {e}")
