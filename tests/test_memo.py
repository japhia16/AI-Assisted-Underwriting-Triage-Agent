import pytest
from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def test_generate_memo_success():
    payload = {
        "submission_json": {
            "property_address": "123 Main St",
            "location_city": "Metropolis",
            "location_state": "NY",
            "occupancy_type": "office",
            "construction_type": "concrete",
            "building_age": 10,
            "sum_insured": 150000,
            "deductible": 1000,
            "prior_claims_count": 0,
            "sprinkler_system": True,
        },
        "pure_premium": 25000,
        "broker_notes": "Sample broker note",
        "preprocessed_json": {"feature_x": 1},
    }

    resp = client.post("/generate-memo", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "memo" in data and data["memo"], "memo missing or empty"
    # Ensure the memo contains the expected section header from the template
    assert ("Property Overview" in data["memo"]) or ("Underwriting Memo" in data["memo"])
    assert "recommended_action" in data


def test_generate_memo_guardrail_failure():
    # pure_premium must be > 0 (schema enforces gt=0) — expect validation error
    payload = {
        "submission_json": {"property_address": "123 Main St"},
        "pure_premium": -500,
    }

    resp = client.post("/generate-memo", json=payload)
    assert resp.status_code == 422, resp.text
