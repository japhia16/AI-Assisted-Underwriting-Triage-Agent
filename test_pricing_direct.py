"""Direct test of the pricing agent with updated field mappings."""
import sys
sys.path.insert(0, '.')

from src.pricing_agent import get_price_and_explanation

# Test submission dict with all required fields (matching intake_agent field names)
test_submission = {
    "occupancy_type": "Warehouse",
    "construction_type": "Non-Combustible",
    "building_age": 10,
    "sum_insured": 5000000,
    "number_of_employees": 25,
    "years_in_business": 5,
    "prior_claims_count": 0,
    "deductible": 100000,
    "sprinkler_system": True,
    "fire_protection": True,
    "business_use": "General Manufacturing",
    "location_city": "Surat",
    "requested_coverage": "Fire and Allied Perils"
}

print("Testing pricing agent with submission:")
print(test_submission)
print("\n" + "="*60)
print("CALLING PRICING AGENT WITH UPDATED FIELD MAPPINGS...")
print("="*60 + "\n")

try:
    result = get_price_and_explanation(test_submission)
    print("\n✅ SUCCESS! Pricing result:")
    print(f"  GLM Baseline:  {result['glm_baseline_INR']}")
    print(f"  XGB Prediction: {result['xgb_prediction_INR']}")
    print(f"  Uplift %:      {result['uplift_pct']}")
    print(f"  Final Premium: {result['final_premium_INR']}")
    print(f"  Top Features:  {result['top_shap_features']}")
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
