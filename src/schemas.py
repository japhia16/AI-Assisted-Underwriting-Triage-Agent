"""
Pydantic schemas for the Intake Agent.
These define the shape of all requests and responses.
"""

from pydantic import BaseModel, Field, model_validator
from typing import Optional, List


class GuardrailValidationError(Exception):
    """Raised when a guardrail check fails and the request should be rejected."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ExtractRequest(BaseModel):
    """
    Input request for the /extract endpoint.
    The user (student, broker, or customer) sends natural-language text here.
    """
    text: str = Field(..., min_length=1, description="Natural-language insurance request")


class SubmissionJSON(BaseModel):
    """
    The structured output after extraction.
    These are the fields the downstream pricing agent expects.
    """
    property_address: Optional[str] = Field(None, description="Full property address")
    location_city: Optional[str] = Field(None, description="City or metropolitan area")
    location_state: Optional[str] = Field(None, description="State or province")
    occupancy_type: Optional[str] = Field(None, description="e.g., office, warehouse, retail, factory")
    construction_type: Optional[str] = Field(None, description="e.g., concrete, steel, brick, wood")
    building_age: Optional[int] = Field(None, ge=0, description="Age in years")
    sum_insured: Optional[float] = Field(None, gt=0, description="Coverage amount in currency units")
    deductible: Optional[float] = Field(None, ge=0, description="Deductible amount")
    prior_claims_count: Optional[int] = Field(None, description="Number of prior insurance claims")
    number_of_employees: int | None = None
    sprinkler_system: Optional[bool] = Field(None, description="Whether sprinkler system is installed")
    fire_protection: Optional[str] = Field(None, description="Fire protection measures (e.g., fire extinguisher, fire station nearby)")
    nearby_hazard_notes: Optional[str] = Field(None, description="Nearby hazards (e.g., industrial area, river)")
    business_use: Optional[str] = Field(None, description="Primary business or use")
    number_of_floors: Optional[int] = Field(None, gt=0, le=160, description="Total number of floors")
    basement_present: Optional[bool] = Field(None, description="Whether basement exists")
    flood_zone_indicator: Optional[str] = Field(None, description="Flood risk indicator (e.g., low, medium, high)")
    storm_exposure_indicator: Optional[str] = Field(None, description="Storm exposure (e.g., coastal, inland)")

    @model_validator(mode="after")
    def check_deductible_vs_sum_insured(self) -> "SubmissionJSON":
        """
        Ensure deductible is not greater than sum_insured when both are provided.
        """
        if self.deductible is not None and self.sum_insured is not None:
            if self.deductible > self.sum_insured:
                raise ValueError("deductible must be less than or equal to sum_insured")
        return self


class ExtractResponse(BaseModel):
    """
    Output response for the /extract endpoint.
    Always includes status, and either submission_json or clarification details.
    """
    status: str = Field(..., description="'complete' or 'needs_clarification'")
    missing_fields: List[str] = Field(default_factory=list, description="List of missing required fields")
    clarifying_question: str = Field(default="", description="Human-readable question for missing info")
    submission_json: SubmissionJSON = Field(..., description="Extracted structured fields")
    preprocessed_json: Optional[dict] = Field(None, description="Output of Student 1's preprocess_submission(), once available")


class PricingHandoff(BaseModel):
    """
    Input payload for underwriting memo generation.
    Contains the structured submission data and optional preprocessed features.
    """
    submission_json: SubmissionJSON = Field(..., description="Structured underwriting submission data")
    preprocessed_json: Optional[dict] = Field(None, description="Optional preprocessed features from the intake pipeline")
    broker_notes: Optional[str] = Field(None, description="Optional broker or underwriter notes")
    pure_premium: Optional[float] = Field(
        None,
        gt=0,
        description="The pure premium value used for underwriting validation and memo generation.",
    )


class MemoResponse(BaseModel):
    """
    Response payload for underwriting memo generation.
    """
    memo: str = Field(..., description="Generated underwriting memo text")
    highlights: List[str] = Field(default_factory=list, description="Highlights or missing-information reminders")
    recommended_action: Optional[str] = Field(
        None,
        description="Derived next action or recommendation for underwriting review.",
    )

