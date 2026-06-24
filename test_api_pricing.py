"""Direct API test: Send a complete submission to the /price endpoint."""
import requests
import json

API_URL = "http://localhost:8000"

# This is a properly formatted submission that matches what the intake agent should extract
submission_json = {
    "property_address": "123 Surat Avenue, Surat, Gujarat",
    "location_city": "Surat",
    "location_state": "Gujarat",
    "occupancy_type": "Warehouse",
    "construction_type": "Non-Combustible",
    "building_age": 10,
    "sum_insured": 5000000.0,
    "deductible": 100000.0,
    "prior_claims_count": 0,
    "number_of_employees": 25,
    "sprinkler_system": True,
    "fire_protection": "Yes",
    "nearby_hazard_notes": None,
    "business_use": "General Manufacturing",
    "number_of_floors": None,
    "basement_present": None,
    "flood_zone_indicator": None,
    "storm_exposure_indicator": None,
    "requested_coverage": "Fire and Allied Perils"
}

print("=" * 70)
print("TESTING PRICING ENDPOINT WITH COMPLETE SUBMISSION")
print("=" * 70)
print("\nSubmission JSON:")
print(json.dumps(submission_json, indent=2))

# Call the /price endpoint
payload = {
    "submission_json": submission_json
}

print("\n" + "=" * 70)
print("CALLING /price ENDPOINT...")
print("=" * 70 + "\n")

try:
    response = requests.post(
        f"{API_URL}/price",
        json=payload,
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}\n")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ SUCCESS! Pricing Response:")
        print("-" * 70)
        print(f"GLM Baseline:        ₹{result['glm_baseline_INR']:,.2f}")
        print(f"XGB Prediction:      ₹{result['xgb_prediction_INR']:,.2f}")
        print(f"Uplift %:            {result['uplift_pct']}%")
        print(f"Final Premium:       ₹{result['final_premium_INR']:,.2f}")
        print("\nTop SHAP Drivers:")
        for i, feature in enumerate(result['top_shap_features'], 1):
            print(f"  {i}. {feature['feature']}")
            print(f"     Impact: {feature['shap_impact']}")
            print(f"     {feature['direction']}")
    else:
        print(f"❌ Error {response.status_code}:")
        print(response.text)
        
except Exception as e:
    print(f"❌ Connection Error: {e}")
    import traceback
    traceback.print_exc()
