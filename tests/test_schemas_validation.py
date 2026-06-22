import pytest
from pydantic import ValidationError
from src.schemas import SubmissionJSON, ExtractResponse


def test_negative_building_age_raises():
    with pytest.raises(ValidationError):
        SubmissionJSON(building_age=-1)


def test_deductible_gt_sum_insured_raises():
    with pytest.raises(ValidationError):
        SubmissionJSON(sum_insured=100000.0, deductible=200000.0)


def test_number_of_floors_bounds():
    with pytest.raises(ValidationError):
        SubmissionJSON(number_of_floors=0)
    with pytest.raises(ValidationError):
        SubmissionJSON(number_of_floors=161)

# Also ensure ExtractResponse model raises when submission_json contains invalid nested SubmissionJSON
def test_extract_response_with_invalid_submission_json_raises():
    bad = {
        "status": "complete",
        "missing_fields": [],
        "clarifying_question": "",
        "submission_json": {"building_age": -5}
    }
    with pytest.raises(ValidationError):
        ExtractResponse(**bad)
