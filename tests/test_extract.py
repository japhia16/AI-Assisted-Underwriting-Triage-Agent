import io

import pypdf
from fastapi.testclient import TestClient
from src.main import app
from src import intake_agent

client = TestClient(app)

COMPLETE_REQUEST_TEXT = (
    "Need a quote for a 15-year-old warehouse in Chennai with concrete construction, "
    "sum insured 2 crore, deductible 1 lakh, no prior claims, sprinkler installed."
)


def test_docs_endpoint_is_available():
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower() or "Swagger UI" in response.text


def test_valid_complete_input(monkeypatch):
    def mock_extract(text: str):
        return {
            "property_address": "123 Example Road",
            "location_city": "Chennai",
            "location_state": "Tamil Nadu",
            "occupancy_type": "Warehouse",
            "construction_type": "Concrete",
            "building_age": 15,
            "sum_insured": 20000000.0,
            "deductible": 100000.0,
            "prior_claims_count": 0,
            "sprinkler_system": True,
            "fire_protection": "Fire extinguishers",
            "nearby_hazard_notes": None,
            "business_use": "Storage",
            "number_of_floors": 2,
            "basement_present": False,
            "flood_zone_indicator": "low",
            "storm_exposure_indicator": "inland",
        }

    monkeypatch.setattr(intake_agent, "extract_with_gemini", mock_extract)
    response = client.post("/extract", json={"text": COMPLETE_REQUEST_TEXT})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert data["missing_fields"] == []
    assert data["clarifying_question"] == ""
    assert data["submission_json"]["location_city"] == "Chennai"


def test_preprocessed_json_present_for_complete(monkeypatch):
    def mock_extract(text: str):
        return {
            "property_address": "123 Example Road",
            "location_city": "Chennai",
            "location_state": "Tamil Nadu",
            "occupancy_type": "Warehouse",
            "construction_type": "Concrete",
            "building_age": 15,
            "sum_insured": 20000000.0,
            "deductible": 100000.0,
            "prior_claims_count": 0,
            "sprinkler_system": True,
            "fire_protection": "Fire extinguishers",
            "nearby_hazard_notes": None,
            "business_use": "Storage",
            "number_of_floors": 2,
            "basement_present": False,
            "flood_zone_indicator": "low",
            "storm_exposure_indicator": "inland",
        }

    monkeypatch.setattr(intake_agent, "extract_with_gemini", mock_extract)
    response = client.post("/extract", json={"text": COMPLETE_REQUEST_TEXT})
    assert response.status_code == 200
    data = response.json()
    # preprocessed_json should be present (stubbed passthrough)
    assert "preprocessed_json" in data
    assert isinstance(data["preprocessed_json"], dict)


def test_missing_required_fields_falls_back_to_clarification(monkeypatch):
    monkeypatch.setattr(intake_agent, "GEMINI_AVAILABLE", False)
    monkeypatch.setattr(intake_agent, "GEMINI_API_KEY", "")

    response = client.post(
        "/extract",
        json={"text": "Need a quote for a 15-year-old warehouse in Chennai with concrete construction and 2 crore sum insured."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "needs_clarification"
    assert "deductible" in data["missing_fields"]
    assert data["clarifying_question"].startswith("Please provide")


def test_empty_input_validation():
    response = client.post("/extract", json={"text": ""})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["details"]


def test_mock_fallback_mode_extracts_expected_fields(monkeypatch):
    monkeypatch.setattr(intake_agent, "GEMINI_AVAILABLE", False)
    monkeypatch.setattr(intake_agent, "GEMINI_API_KEY", "")

    response = client.post(
        "/extract",
        json={"text": "Request quote for a 10-year-old office building in Hyderabad with concrete construction, 2 crore sum insured, no prior claims."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["submission_json"]["location_city"] == "Hyderabad"
    assert data["submission_json"]["occupancy_type"] == "Office"
    assert data["submission_json"]["construction_type"] == "Concrete"
    assert data["status"] == "needs_clarification"


def test_generate_clarification_question_message():
    question_single = intake_agent.generate_clarification_question(["location_city"])
    assert question_single == "Please provide the city."

    question_multiple = intake_agent.generate_clarification_question(["building_age", "deductible"])
    assert "building age" in question_multiple
    assert "deductible" in question_multiple
    assert question_multiple.startswith("Please provide the following")


def test_contradictory_information_triggers_clarification(monkeypatch):
    # Use the exact text from test_samples.md Test Case 4
    text = "The building is 5 years old and also built in 1998. Location is Mumbai, warehouse, concrete, 50 lakh, deductible 10000."

    # Use the real extraction logic (mocked to return fields similar to Gemini)
    def mock_extract(text_in: str):
        return {
            "property_address": None,
            "location_city": "Mumbai",
            "location_state": None,
            "occupancy_type": "Warehouse",
            "construction_type": "Concrete",
            "building_age": 5,
            "sum_insured": 5000000,
            "deductible": 10000,
            "prior_claims_count": None,
            "sprinkler_system": None,
            "fire_protection": None,
            "nearby_hazard_notes": None,
            "business_use": None,
            "number_of_floors": None,
            "basement_present": None,
            "flood_zone_indicator": None,
            "storm_exposure_indicator": None,
        }

    monkeypatch.setattr(intake_agent, "extract_with_gemini", mock_extract)
    response = client.post("/extract", json={"text": text})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "needs_clarification"
    assert "building_age" in data["missing_fields"]
    assert data["clarifying_question"].startswith("Please provide the building age")


def test_upload_submission_pdf(monkeypatch):
    # Create an in-memory PDF file containing a simple insurance request.
    pdf_stream = io.BytesIO()
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_metadata({"/Title": "Test PDF"})
    writer.write(pdf_stream)

    # Note: pypdf does not easily embed text in blank pages without additional setup,
    # so we can instead use the same extraction logic against text if parsing sees no text.
    # Use a monkeypatch for the extraction on the extracted text to validate the endpoint flow.
    pdf_stream.seek(0)

    def mock_process_request(text: str):
        assert isinstance(text, str)
        return {
            "status": "complete",
            "missing_fields": [],
            "clarifying_question": "",
            "submission_json": {
                "property_address": "123 Example Road",
                "location_city": "Chennai",
                "location_state": "Tamil Nadu",
                "occupancy_type": "Warehouse",
                "construction_type": "Concrete",
                "building_age": 15,
                "sum_insured": 20000000.0,
                "deductible": 100000.0,
                "prior_claims_count": 0,
                "sprinkler_system": True,
                "fire_protection": "Fire extinguishers",
                "nearby_hazard_notes": None,
                "business_use": "Storage",
                "number_of_floors": 2,
                "basement_present": False,
                "flood_zone_indicator": "low",
                "storm_exposure_indicator": "inland",
            },
            "preprocessed_json": {},
        }

    monkeypatch.setattr("src.main.process_request", mock_process_request)

    response = client.post(
        "/upload-submission",
        files={"file": ("test.pdf", pdf_stream.getvalue(), "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert data["submission_json"]["location_city"] == "Chennai"
