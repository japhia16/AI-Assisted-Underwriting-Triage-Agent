from src.preprocessing_stub import preprocess_submission

test = {
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

try:
    print("Running Preprocessing Integration Test...")
    result = preprocess_submission(test)
    print("✅ SUCCESS!")
    print(f"Shape: {result.shape}")
    print(f"Columns (first 10): {list(result.columns)[:10]}")
except FileNotFoundError as e:
    print(f"❌ ERROR: {e}")
