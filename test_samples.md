# Sample Test Cases for the Intake Agent

Use these test cases to verify the Intake Agent works correctly.

## Test Case 1: Complete Input

**Status**: Expected: `complete`

**Input:**
```json
{
  "text": "Need a quote for a 10-year-old office building in Hyderabad, reinforced concrete, sum insured 2 crore, deductible 1 lakh, no prior claims, sprinkler installed."
}
```

**How to test in Swagger:**
1. Go to http://localhost:8000/docs
2. Click on POST /extract
3. Click "Try it out"
4. Paste the input in the "Request body" field
5. Click "Execute"

**Expected Output:**
```json
{
  "status": "complete",
  "missing_fields": [],
  "clarifying_question": "",
  "submission_json": {
    "property_address": null,
    "location_city": "Hyderabad",
    "location_state": null,
    "occupancy_type": "Office",
    "construction_type": "Concrete",
    "building_age": 10,
    "sum_insured": 20000000,
    "deductible": 100000,
    "prior_claims_count": 0,
    "sprinkler_system": true,
    "fire_protection": null,
    "nearby_hazard_notes": null,
    "business_use": null,
    "number_of_floors": null,
    "basement_present": null,
    "flood_zone_indicator": null,
    "storm_exposure_indicator": null
  }
}
```

---

## Test Case 2: Missing Key Fields

**Status**: Expected: `needs_clarification`

**Input:**
```json
{
  "text": "Need a quote for my warehouse."
}
```

**Expected Output:**
```json
{
  "status": "needs_clarification",
  "missing_fields": [
    "location_city",
    "occupancy_type",
    "construction_type",
    "building_age",
    "sum_insured",
    "deductible"
  ],
  "clarifying_question": "Please provide the following: city, occupancy type (e.g., warehouse, office), construction type (e.g., concrete, steel), building age, sum insured / coverage amount, deductible.",
  "submission_json": {
    "property_address": null,
    "location_city": null,
    "location_state": null,
    "occupancy_type": "Warehouse",
    "construction_type": null,
    "building_age": null,
    "sum_insured": null,
    "deductible": null,
    "prior_claims_count": null,
    "sprinkler_system": null,
    "fire_protection": null,
    "nearby_hazard_notes": null,
    "business_use": null,
    "number_of_floors": null,
    "basement_present": null,
    "flood_zone_indicator": null,
    "storm_exposure_indicator": null
  }
}
```

---

## Test Case 3: Informal/Messy Input

**Status**: Expected: `needs_clarification` (missing deductible)

**Input:**
```json
{
  "text": "Hey, I've got this old factory near Vizag, maybe 20 years, insured around 3 cr, not sure deductible yet, one claim before."
}
```

**Expected Output:**
```json
{
  "status": "needs_clarification",
  "missing_fields": [
    "deductible"
  ],
  "clarifying_question": "Please provide the deductible.",
  "submission_json": {
    "property_address": null,
    "location_city": "Vizag",
    "location_state": null,
    "occupancy_type": "Factory",
    "construction_type": null,
    "building_age": 20,
    "sum_insured": 30000000,
    "deductible": null,
    "prior_claims_count": 1,
    "sprinkler_system": null,
    "fire_protection": null,
    "nearby_hazard_notes": null,
    "business_use": null,
    "number_of_floors": null,
    "basement_present": null,
    "flood_zone_indicator": null,
    "storm_exposure_indicator": null
  }
}
```

---

## Test Case 4: Contradictory Information

**Status**: Expected: `needs_clarification`

**Input:**
```json
{
  "text": "The building is 5 years old and also built in 1998. Location is Mumbai, warehouse, concrete, 50 lakh, deductible 10000."
}
```

**Expected Output:**
```json
{
  "status": "needs_clarification",
  "missing_fields": [
    "building_age"
  ],
  "clarifying_question": "Please provide the building age. (Note: Conflicting information detected.)",
  "submission_json": {
    "property_address": null,
    "location_city": "Mumbai",
    "location_state": null,
    "occupancy_type": "Warehouse",
    "construction_type": "Concrete",
    "building_age": null,
    "sum_insured": 5000000,
    "deductible": 10000,
    "prior_claims_count": null,
    "sprinkler_system": null,
    "fire_protection": null,
    "nearby_hazard_notes": null,
    "business_use": null,
    "number_of_floors": null,
    "basement_present": null,
    "flood_zone_indicator": null,
    "storm_exposure_indicator": null
  }
}
```

---

## Test Case 5: Different Phrasing by Broker

**Status**: Expected: `complete`

**Input:**
```json
{
  "text": "Request indication for a steel-frame logistics warehouse, Chennai region, insured value 40M, fire protection standard, two prior claims, building age 15 years, deductible 2 lakh."
}
```

**Expected Output:**
```json
{
  "status": "complete",
  "missing_fields": [],
  "clarifying_question": "",
  "submission_json": {
    "property_address": null,
    "location_city": "Chennai",
    "location_state": null,
    "occupancy_type": "Warehouse",
    "construction_type": "Steel",
    "building_age": 15,
    "sum_insured": 40000000,
    "deductible": 200000,
    "prior_claims_count": 2,
    "sprinkler_system": null,
    "fire_protection": "Standard",
    "nearby_hazard_notes": null,
    "business_use": "Logistics",
    "number_of_floors": null,
    "basement_present": null,
    "flood_zone_indicator": null,
    "storm_exposure_indicator": null
  }
}
```

---

## Running Tests Programmatically

You can also write Python tests using `requests` or `httpx`:

```python
import requests

BASE_URL = "http://localhost:8000"

def test_complete_input():
    response = requests.post(
        f"{BASE_URL}/extract",
        json={
            "text": "Need a quote for a 10-year-old office building in Hyderabad, reinforced concrete, sum insured 2 crore, deductible 1 lakh, no prior claims, sprinkler installed."
        }
    )
    
    result = response.json()
    assert result["status"] == "complete", f"Expected 'complete', got '{result['status']}'"
    assert len(result["missing_fields"]) == 0, f"Expected no missing fields, got {result['missing_fields']}"
    print("✓ Test Case 1 PASSED: Complete input")

def test_missing_fields():
    response = requests.post(
        f"{BASE_URL}/extract",
        json={"text": "Need a quote for my warehouse."}
    )
    
    result = response.json()
    assert result["status"] == "needs_clarification", f"Expected 'needs_clarification', got '{result['status']}'"
    assert len(result["missing_fields"]) > 0, "Expected missing fields"
    print("✓ Test Case 2 PASSED: Missing fields")

if __name__ == "__main__":
    test_complete_input()
    test_missing_fields()
    print("\nAll tests passed!")
```

Save this as `test_intake.py` and run:
```bash
python test_intake.py
```
