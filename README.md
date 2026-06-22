# Insurance Intake Agent - Student 4 Starter Code

## Overview

This is the **Intake Agent** for the Agent-Assisted Commercial Property Insurance Quote Recommendation System. Its sole responsibility is to:

1. Accept natural-language insurance requests from brokers or customers
2. Extract structured underwriting fields using the **Gemini API** with schema-constrained JSON output
3. Validate that all required fields are present
4. Return either complete structured JSON or a clarification request
5. **Never** calculate premium, risk score, severity, or underwriting decisions

## Quick Start

### 1. Set Up Virtual Environment

```bash
# On Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# On macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Then edit `.env` and add your Gemini API key:

```
GEMINI_API_KEY=your_actual_api_key_here
```

**Get your Gemini API key:** https://ai.google.dev/

### 4. Run the FastAPI Server

```bash
uvicorn src.main:app --reload
```

The server will start at `http://localhost:8000`

### 5. Test the API

#### Option A: Interactive Swagger Docs (Recommended)

Open your browser and navigate to:
```
http://localhost:8000/docs
```

Click on the `POST /extract` endpoint, then click "Try it out" and paste a test request:

```json
{
  "text": "Need a quote for a 15-year-old warehouse in Chennai with concrete construction and 2 crore sum insured."
}
```

Click "Execute" to see the response.

#### Option B: Using curl

```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Need a quote for a 10-year-old office building in Hyderabad, reinforced concrete, sum insured 2 crore, deductible 1 lakh, no prior claims, sprinkler installed."
  }'
```

#### Option C: Using Python

```python
import requests

response = requests.post(
    "http://localhost:8000/extract",
    json={
        "text": "Need a quote for a 10-year-old office building in Hyderabad, reinforced concrete, sum insured 2 crore, deductible 1 lakh, no prior claims, sprinkler installed."
    }
)

print(response.json())
```

## Underwriter Memo Agent (`POST /generate-memo`)

The repository exposes a dedicated endpoint for formatting an underwriting memo
from the structured submission data produced by the Intake Agent (and any
preprocessing performed by Student 1). This agent is strictly a formatting and
handoff service — it does not perform pricing, scoring, or final underwriting
decisions.

Endpoint: `POST /generate-memo`

Input: `PricingHandoff` (JSON)
- `submission_json` (object): `SubmissionJSON` produced by the Intake Agent.
- `preprocessed_json` (object, optional): Optional features produced by Student 1 preprocessing.
- `broker_notes` (string, optional): Freeform notes to include in the memo.
- `pure_premium` (number, optional): Numeric pure premium if available. When
  provided it must be > 0.

Output: `MemoResponse` (JSON)
- `memo` (string): The generated underwriting memo in Markdown-style sections.
- `highlights` (list[string]): Missing-field reminders or important notes.
- `recommended_action` (string | null): Always a neutral, non-binding handoff
  text. Student 4 does not make binding underwriting decisions.

DataIntegrityGuardrail
- The memo agent includes a guardrail that validates key numeric inputs before
  invoking any LLM. For example, `pure_premium` must be greater than zero. If
  validation fails the request is rejected and the agent will not forward the
  malformed data to the model.

Fallback behavior (CI/CD resilience)
- The memo agent attempts to use Agno + Gemini when available. If the required
  SDKs or API keys are not present, or the model call fails in runtime, the
  agent returns a deterministic template-based memo instead. This ensures
  deterministic test runs and CI stability even when external AI services are
  unavailable.

Integration note
- The memo output is a human-readable handoff for underwriters. Any actual
  pricing, binding, or underwriting decisions must be made downstream by the
  underwriting system (Student 3 / production underwriting service).


## File Structure

```
insurance-intake-agent/
├── src/
│   ├── __init__.py           # Makes src a Python package
│   ├── intake_agent.py       # Core extraction logic using Gemini
│   ├── main.py              # FastAPI application
│   └── schemas.py           # Pydantic request/response models
├── .env.example             # Template for environment variables
├── .gitignore               # Git ignore (if using version control)
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Key Concepts

### Pydantic Schemas (`schemas.py`)

- **ExtractRequest**: Defines the input (natural-language text)
- **SubmissionJSON**: Defines all extractable insurance fields
- **ExtractResponse**: Defines the output (status, missing fields, clarification, and structured JSON)

Pydantic validates incoming requests and ensures outgoing responses match the schema.

### Intake Agent (`intake_agent.py`)

**Main function: `process_request(text)`**

1. Validates the input text (rejects empty/null)
2. Calls **Gemini API** with structured output to extract fields
3. Falls back to **mock extraction** if Gemini is unavailable (useful for testing)
4. Validates that all required fields are present
5. Returns status ("complete" or "needs_clarification")
6. Generates clarification questions if fields are missing

**Required Fields:**
- `location_city` ✓
- `occupancy_type` ✓
- `construction_type` ✓
- `building_age` ✓
- `sum_insured` ✓
- `deductible` ✓

If any of these are missing, status = "needs_clarification"

### FastAPI Server (`main.py`)

**Endpoint: POST /extract**

- Accepts request body with natural-language text
- Calls the Intake Agent to process the request
- Returns structured JSON response
- Includes Swagger docs at `/docs`

## Extracted Fields

The Intake Agent attempts to extract these fields:

| Field | Type | Description | Required? |
|-------|------|-------------|-----------|
| `property_address` | string | Full property address | No |
| `location_city` | string | City or metropolitan area | **Yes** |
| `location_state` | string | State or province | No |
| `occupancy_type` | string | e.g., office, warehouse, retail | **Yes** |
| `construction_type` | string | e.g., concrete, steel, brick | **Yes** |
| `building_age` | integer | Age in years | **Yes** |
| `sum_insured` | float | Coverage amount | **Yes** |
| `deductible` | float | Deductible amount | **Yes** |
| `prior_claims_count` | integer | Number of prior claims | No |
| `sprinkler_system` | boolean | Sprinkler system installed? | No |
| `fire_protection` | string | Fire protection measures | No |
| `nearby_hazard_notes` | string | Nearby hazards | No |
| `business_use` | string | Primary business/use | No |
| `number_of_floors` | integer | Number of floors | No |
| `basement_present` | boolean | Basement exists? | No |
| `flood_zone_indicator` | string | Flood risk (low/medium/high) | No |
| `storm_exposure_indicator` | string | Storm exposure (coastal/inland) | No |

## Sample Test Cases

### Test Case 1: Complete Input (Expected: status = "complete")

**Input:**
```json
{
  "text": "Need a quote for a 10-year-old office building in Hyderabad, reinforced concrete, sum insured 2 crore, deductible 1 lakh, no prior claims, sprinkler installed."
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

### Test Case 2: Missing Key Fields (Expected: status = "needs_clarification")

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
  "missing_fields": ["location_city", "occupancy_type", "construction_type", "building_age", "sum_insured", "deductible"],
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

### Test Case 3: Informal/Messy Input (Expected: Partial extraction + clarification)

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
  "missing_fields": ["deductible"],
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

## Integrating with Student 1 Preprocessing Pipeline

This Intake Agent is strictly an extraction service. It does not expose `/price` or `/extract-and-price` endpoints, and it does not include `pricing_agent.py`.

Use the response as follows:

- If `status == "complete"`: `submission_json` contains validated structured fields ready for Student 1 preprocessing.
- If `status == "needs_clarification"`: use `clarifying_question` to request missing or contradictory information.

Example integration:

```python
import requests

response = requests.post(
    "http://localhost:8000/extract",
    json={"text": user_input}
)
result = response.json()

if result["status"] == "complete":
    submission_json = result["submission_json"]
    # pass submission_json to Student 1 preprocessing
else:
    print(result["clarifying_question"])
```

## Fallback: Mock Extraction Mode

If the Gemini API is unavailable or not configured, the Intake Agent automatically falls back to **mock extraction**. This uses simple heuristics to extract fields (useful for testing without API access).

Mock extraction:
- ✓ Works without API key
- ✓ Great for local testing and demos
- ✗ Less accurate than Gemini
- ✗ May miss nuanced information

To force mock mode, delete or comment out the `GEMINI_API_KEY` in `.env`.

## Running Tests

To run automated tests (if added):

```bash
pytest
```

## Common Issues & Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'google.generativeai'"

**Solution**: Install Gemini SDK:
```bash
pip install google-generativeai
```

### Issue: "GEMINI_API_KEY not found"

**Solution**: Make sure `.env` exists and contains:
```
GEMINI_API_KEY=your_key_here
```

### Issue: "Connection refused on localhost:8000"

**Solution**: Make sure the FastAPI server is running:
```bash
uvicorn src.main:app --reload
```

### Issue: Extraction returns mostly null fields

**Solution**: 
- If using mock mode, that's expected (mock is simple)
- If using Gemini, check that your API key is valid
- Provide more detailed text to extract from

## Next Steps for Extension

1. Add database persistence for extracted requests
2. Add user authentication to the API
3. Build integration tests with sample requests
4. Add logging to a file for debugging
5. Deploy to a cloud platform (Google Cloud, AWS, etc.)

## Notes for Downstream Integration

- Always check `status` before using `submission_json`
- Use the `clarifying_question` to prompt users when needed
- Assume `submission_json` is complete and valid when `status == "complete"`
- Never modify the extracted fields before passing them to Student 1 preprocessing or downstream workflows

## Rules

The Intake Agent **will not**:
- ✗ Calculate premiums
- ✗ Assign risk levels or underwriting decisions
- ✗ Guess missing values
- ✗ Rewrite user input in paragraph form

The Intake Agent **will**:
- ✓ Extract structured fields from natural language
- ✓ Validate against required fields
- ✓ Ask clarification questions when needed
- ✓ Return valid JSON only

---

**Questions?** Check the docstrings in `src/intake_agent.py` and `src/main.py` for detailed explanations.
