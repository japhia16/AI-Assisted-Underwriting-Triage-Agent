"""
Intake Agent: Extract structured insurance information from natural-language requests.
Uses Gemini API with structured outputs to enforce JSON schema compliance.
Falls back to mock extraction if Gemini is unavailable.
"""

import os
import json
import logging
import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv
from src.preprocessing_stub import preprocess_submission
from src.schemas import SubmissionJSON

# Load environment variables from .env file
load_dotenv()

# Configure logger for this module (app-level configuration is done in main.py)
logger = logging.getLogger(__name__)

# Gemini API key (loaded from .env or environment)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Gemini SDK state variables
GEMINI_AVAILABLE = None
_client = None


def _initialize_gemini() -> bool:
    """Lazily import and configure the Gemini SDK (google-genai client).

    Uses `genai.Client(api_key=...)` and stores the client in module `_client`.
    """
    global GEMINI_AVAILABLE, _client
    if GEMINI_AVAILABLE is not None:
        return GEMINI_AVAILABLE

    if not GEMINI_API_KEY:
        GEMINI_AVAILABLE = False
        return False

    try:
        # new maintained package exposes `genai` under `google`
        from google import genai as genai_module
        _client = genai_module.Client(api_key=GEMINI_API_KEY)
        GEMINI_AVAILABLE = True
    except Exception as e:
        GEMINI_AVAILABLE = False
        logger.warning("Gemini client init failed (%s). Using mock extraction mode.", e)
        return False

    return GEMINI_AVAILABLE

# Required fields for downstream workflow
REQUIRED_FIELDS = [
    "location_city",
    "occupancy_type",
    "construction_type",
    "building_age",
    "sum_insured",
    "deductible",
]


def extract_with_gemini(text: str) -> Dict[str, Any]:
    """
    Send text to Gemini and get structured JSON extraction.
    Gemini's structured output mode ensures schema-compliant JSON.
    
    Args:
        text (str): Natural-language insurance request
        
    Returns:
        Dict with extracted fields or error state
    """
    if not _initialize_gemini() or not GEMINI_API_KEY:
        logger.info("Gemini unavailable or API key missing; falling back to mock extraction.")
        return extract_with_mock(text)
    
    try:
        # Define the schema for Gemini structured output
        schema = {
            "type": "OBJECT",
            "properties": {
                "property_address": {"type": "STRING"},
                "location_city": {"type": "STRING"},
                "location_state": {"type": "STRING"},
                "occupancy_type": {"type": "STRING"},
                "construction_type": {"type": "STRING"},
                "building_age": {"type": "INTEGER"},
                "sum_insured": {"type": "NUMBER"},
                "deductible": {"type": "NUMBER"},
                "prior_claims_count": {"type": "INTEGER"},
                "sprinkler_system": {"type": "BOOLEAN"},
                "fire_protection": {"type": "STRING"},
                "nearby_hazard_notes": {"type": "STRING"},
                "business_use": {"type": "STRING"},
                "number_of_floors": {"type": "INTEGER"},
                "number_of_employees": {"type": "INTEGER"},
                "basement_present": {"type": "BOOLEAN"},
                "flood_zone_indicator": {"type": "STRING"},
                "storm_exposure_indicator": {"type": "STRING"},
                "requested_coverage": {"type": "STRING"},
            },
        }
        
        # Craft the prompt for Gemini
        prompt = f"""You are an insurance information extraction assistant. Extract structured underwriting information from the following customer request. Return ONLY valid JSON matching this exact structure, with no markdown or explanation.

Customer request: {text}

Return JSON with these fields (use null for missing/unknown values):
- property_address
- location_city
- location_state
- occupancy_type
- construction_type
- building_age (number)
- sum_insured (number)
- deductible (number)
- prior_claims_count (number)
- sprinkler_system (boolean)
- fire_protection
- nearby_hazard_notes
- business_use
- number_of_floors (number)
- basement_present (boolean)
- flood_zone_indicator
- storm_exposure_indicator
- requested_coverage

Do NOT calculate premium, risk score, or underwriting decision. Extract only what is stated or clearly implied."""
        prompt = f"""You are an insurance information extraction assistant. Extract structured underwriting information from the following customer request. Return ONLY valid JSON matching this exact structure, with no markdown or explanation.

    Customer request: {text}

    Return JSON with these fields (use null for missing/unknown values):
    - property_address
    - location_city
    - location_state
    - occupancy_type
    - construction_type
    - building_age (number)
    - sum_insured (number)
    - deductible (number)
    - prior_claims_count (number)
    - number_of_employees (number)
    - sprinkler_system (boolean)
    - fire_protection
    - nearby_hazard_notes
    - business_use
    - number_of_floors (number)
    - basement_present (boolean)
    - flood_zone_indicator
    - storm_exposure_indicator
    - requested_coverage

    Important formatting notes for numeric fields:
    - When returning monetary values such as `sum_insured` or `deductible`, return them as plain numeric values (no currency symbols, no commas). For example, return 40000000 rather than "$40,000,000".
    - When returning counts such as `prior_claims_count` and `number_of_employees`, return integers that correspond to the labels "Prior Claims" and "Employees" in the text. Do not confuse the two.

    Do NOT calculate premium, risk score, or underwriting decision. Extract only what is stated or clearly implied."""
        
        # Call Gemini API with the new google-genai client, requesting Pydantic
        # `SubmissionJSON` as the response schema. Fall back to mock on any error.
        try:
            response = _client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": SubmissionJSON,
                    "max_output_tokens": 1024,
                },
            )

            text_response = getattr(response, "text", None) or str(response)
            text_response = text_response.strip()
            try:
                extracted = json.loads(text_response)
            except json.JSONDecodeError:
                extracted = _parse_json_from_text(text_response)

            logger.info(f"Gemini extraction succeeded: {extracted}")
            return extracted
        except Exception as e:
            logger.warning(f"Gemini generate_content failed: {e}; falling back to mock.")
            return extract_with_mock(text)

    except Exception as e:
        logger.error(f"Gemini extraction failed: {e}. Falling back to mock mode.")
        return extract_with_mock(text)


def _parse_json_from_text(text: str) -> Dict[str, Any]:
    """
    Extract the first JSON object from Gemini text output.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or start > end:
        raise ValueError(f"No JSON object found in Gemini response: {text!r}")

    json_text = text[start:end + 1]
    return json.loads(json_text)


def extract_with_mock(text: str) -> Dict[str, Any]:
    """
    Fallback mock extraction when Gemini is unavailable.
    Uses simple heuristics to extract key fields from text.
    Useful for testing and demonstration.
    
    Args:
        text (str): Natural-language insurance request
        
    Returns:
        Dict with extracted fields (many will be null)
    """
    logger.info("Using mock extraction (Gemini unavailable).")
    
    # Initialize all fields as None
    result = {
        "property_address": None,
        "location_city": None,
        "location_state": None,
        "occupancy_type": None,
        "construction_type": None,
        "building_age": None,
        "sum_insured": None,
        "deductible": None,
        "prior_claims_count": None,
        "sprinkler_system": None,
        "fire_protection": None,
        "nearby_hazard_notes": None,
        "business_use": None,
        "number_of_floors": None,
        "basement_present": None,
        "flood_zone_indicator": None,
        "storm_exposure_indicator": None,
        "requested_coverage": None,
    }
    
    # Simple heuristic extraction (very basic)
    text_lower = text.lower()
    
    # Try to find city names (very simplistic)
    cities = ["hyderabad", "bangalore", "delhi", "mumbai", "chennai", "pune", "ahmedabad", "vizag"]
    for city in cities:
        if city in text_lower:
            result["location_city"] = city.capitalize()
            break

    # If an Address: line is present, try to extract the city from it (comma-separated)
    for line in text.splitlines():
        if "address" in line.lower():
            parts = line.split(":", 1)
            if len(parts) > 1:
                addr = parts[1].strip()
                result["property_address"] = addr
                # attempt to get city as the next comma-separated token
                tokens = [p.strip() for p in addr.split(",") if p.strip()]
                if len(tokens) >= 2:
                    # choose the second token as city (common pattern: street, city, state)
                    result["location_city"] = tokens[1]
            break
    
    # Try to find occupancy type
    occupancies = ["warehouse", "office", "factory", "retail", "store", "building"]
    for occ in occupancies:
        if occ in text_lower:
            result["occupancy_type"] = occ.capitalize()
            break
    
    # Try to find construction type
    constructions = ["concrete", "steel", "brick", "wood", "reinforced", "fire resistive", "masonry", "tilt-up"]
    for const in constructions:
        if const in text_lower:
            result["construction_type"] = const.title()
            break

    # Also check for explicit 'Construction' or 'Construction Class' lines and use their value
    for line in text.splitlines():
        if "construction" in line.lower():
            parts = line.split(":", 1)
            if len(parts) > 1:
                val = parts[1].strip()
                # prefer explicit value from the line
                result["construction_type"] = val
            break
    
    # Try to extract age (very simplistic: look for number + "year")
    import re
    age_match = re.search(r"(\d+)\s*-?\s*year", text_lower)
    if age_match:
        result["building_age"] = int(age_match.group(1))
    
    # Try to extract sum insured (look for "crore", "lakh", "million", etc.)
    # First, look for explicit monetary patterns on their lines (e.g., "$40,000,000", "Total Sum Insured: $40,000,000")
    for line in text.splitlines():
        if "sum insured" in line.lower() or "total sum insured" in line.lower():
            m = re.search(r"[\$₹€]?\s*([\d,]+(?:\.\d+)?)", line)
            if m:
                num = float(m.group(1).replace(",", ""))
                result["sum_insured"] = num
                break

    # If not found, fall back to unit-aware parsing (crore/lakh/million/thousand)
    if result["sum_insured"] is None:
        sum_match = re.search(r"([\d.]+)\s*(crore|lakh|million|thousand)", text_lower)
        if sum_match:
            value = float(sum_match.group(1))
            unit = sum_match.group(2).lower()
            if "crore" in unit:
                result["sum_insured"] = value * 10000000
            elif "lakh" in unit:
                result["sum_insured"] = value * 100000
            elif "million" in unit:
                result["sum_insured"] = value * 1000000
            elif "thousand" in unit:
                result["sum_insured"] = value * 1000
    
    # Check for sprinkler system
    if "sprinkler" in text_lower:
        result["sprinkler_system"] = "installed" in text_lower or "present" in text_lower
    
    # Extract number of employees (line-oriented to avoid picking numbers from other lines)
    result["number_of_employees"] = None
    for line in text.splitlines():
        if "employee" in line.lower():
            m = re.search(r"(\d+)", line)
            if m:
                result["number_of_employees"] = int(m.group(1))
                break

    # Extract deductible similarly (look for 'deductible' on its line)
    for line in text.splitlines():
        if "deductible" in line.lower():
            m = re.search(r"[\$₹€]?\s*([\d,]+(?:\.\d+)?)", line)
            if m:
                result["deductible"] = float(m.group(1).replace(",", ""))
                break

    # Check for prior claims (prefer explicit 'Prior Claims: N' on the same line)
    result["prior_claims_count"] = None
    for line in text.splitlines():
        if "prior" in line.lower() and "claim" in line.lower():
            m = re.search(r"(\d+)", line)
            if m:
                result["prior_claims_count"] = int(m.group(1))
                break
    # Fallback: look for a nearby pattern, but only if above did not find it
    if result["prior_claims_count"] is None:
        claims_match = re.search(r"(\d+)\s*(?:prior\s*)?claim", text_lower)
        if claims_match:
            result["prior_claims_count"] = int(claims_match.group(1))

    # Extract requested coverage if explicitly mentioned
    if result["requested_coverage"] is None:
        if "coverage required" in text_lower or "requested coverage" in text_lower or "coverage:" in text_lower:
            if "fire and allied" in text_lower or "allied perils" in text_lower:
                result["requested_coverage"] = "Fire and Allied Perils"
            elif "property all risk" in text_lower or "all risk" in text_lower:
                result["requested_coverage"] = "Property All Risk"
            elif "fire only" in text_lower:
                result["requested_coverage"] = "Fire Only"
            elif "fire + burglary" in text_lower or "fire and burglary" in text_lower or "burglary" in text_lower:
                result["requested_coverage"] = "Fire + Burglary"
            elif "standard fire" in text_lower or "special perils" in text_lower:
                result["requested_coverage"] = "Standard Fire & Special Perils"

    return result


def validate_required_fields(extracted: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Check if all required fields are present and non-null.
    
    Args:
        extracted (Dict): The extracted fields
        
    Returns:
        Tuple of (is_complete, missing_fields)
    """
    missing = []
    for field in REQUIRED_FIELDS:
        if field not in extracted or extracted[field] is None:
            missing.append(field)
    
    return len(missing) == 0, missing


def generate_clarification_question(missing_fields: List[str]) -> str:
    """
    Generate a human-readable clarification question based on missing fields.
    
    Args:
        missing_fields (List[str]): List of required fields that are missing
        
    Returns:
        str: A clarification question
    """
    field_labels = {
        "location_city": "city",
        "occupancy_type": "occupancy type (e.g., warehouse, office)",
        "construction_type": "construction type (e.g., concrete, steel)",
        "building_age": "building age",
        "sum_insured": "sum insured / coverage amount",
        "deductible": "deductible",
    }
    
    labels = [field_labels.get(f, f) for f in missing_fields]
    if len(labels) == 1:
        return f"Please provide the {labels[0]}."
    else:
        return f"Please provide the following: {', '.join(labels)}."


def process_request(text: str) -> Dict[str, Any]:
    """
    Main entry point: process a natural-language request and return structured JSON.
    
    Args:
        text (str): Natural-language insurance request
        
    Returns:
        Dict with status, missing_fields, clarifying_question, and submission_json
    """
    # Validate input
    if not text or not text.strip():
        return {
            "status": "needs_clarification",
            "missing_fields": REQUIRED_FIELDS,
            "clarifying_question": "Please provide your insurance request.",
            "submission_json": {
                "property_address": None,
                "location_city": None,
                "location_state": None,
                "occupancy_type": None,
                "construction_type": None,
                "building_age": None,
                "sum_insured": None,
                "deductible": None,
                "prior_claims_count": None,
                "sprinkler_system": None,
                "fire_protection": None,
                "nearby_hazard_notes": None,
                "business_use": None,
                "number_of_floors": None,
                "basement_present": None,
                "flood_zone_indicator": None,
                "storm_exposure_indicator": None,
            },
        }
    
    # Extract using Gemini (or mock)
    extracted = extract_with_gemini(text.strip())

    # Detect simple contradictions in the raw text that affect extracted fields
    def detect_contradictions(text: str, extracted: Dict[str, Any]) -> List[str]:
        """
        Return list of field names that have contradictory mentions in the raw text.
        Currently detects contradictions for `building_age` by looking for both
        explicit ages (e.g., "5 years") and explicit years (e.g., "1998") that
        imply a different age.
        """
        contradictions: List[str] = []
        import re

        # Find explicit age mentions like '5 year' or '5-year-old'
        age_matches = re.findall(r"(\d+)\s*-?\s*year", text.lower())
        ages = {int(m) for m in age_matches} if age_matches else set()

        # Find explicit 4-digit years like 1998 or 2005
        year_matches = re.findall(r"\b(19|20)\d{2}\b", text)
        years = set()
        if year_matches:
            # re.findall with this pattern returns the century part; extract full years separately
            years = set(int(y) for y in re.findall(r"\b((?:19|20)\d{2})\b", text))

        # Compute implied ages from years using current year
        implied_ages = set()
        if years:
            now_year = datetime.datetime.now().year
            for y in years:
                if 1800 < y <= now_year:
                    implied_ages.add(now_year - y)

        # Combine and detect disagreement
        all_ages = set(ages) | implied_ages
        if len(all_ages) > 1:
            # Multiple distinct age indicators found -> contradiction
            contradictions.append("building_age")

        return contradictions

    
    # Validate required fields
    is_complete, missing = validate_required_fields(extracted)

    # Apply contradiction detection and adjust extracted fields/flags
    contradictions = detect_contradictions(text, extracted)
    if "building_age" in contradictions:
        # Null out any extracted building_age to avoid downstream misinterpretation
        extracted["building_age"] = None
        if "building_age" not in missing:
            missing.append("building_age")
        # If we previously thought this was complete, downgrade to needs_clarification
        if is_complete:
            is_complete = False

    
    # Build response
    if is_complete:
        status = "complete"
        clarification = ""
    else:
        status = "needs_clarification"
        clarification = generate_clarification_question(missing)

    # If a contradiction was detected for building_age, append the note
    if "building_age" in contradictions:
        if clarification:
            clarification = f"{clarification} (Note: Conflicting information detected.)"
        else:
            clarification = "Please provide the building age. (Note: Conflicting information detected.)"
    
    response = {
        "status": status,
        "missing_fields": missing,
        "clarifying_question": clarification,
        "submission_json": extracted,
        "preprocessed_json": None,
    }
    
    logger.info(f"Process result: {response}")
    # If complete, call the preprocessing seam to prepare features for downstream pricing
    if status == "complete":
        try:
            preprocessed = preprocess_submission(extracted)
            # Convert DataFrame result to a plain dict for JSON/Pydantic
            try:
                if hasattr(preprocessed, "to_dict"):
                    response["preprocessed_json"] = preprocessed.to_dict(orient="records")[0]
                elif isinstance(preprocessed, dict):
                    response["preprocessed_json"] = preprocessed
                else:
                    response["preprocessed_json"] = dict(preprocessed)
            except Exception:
                # Fallback: don't include preprocessed JSON if conversion fails
                logger.warning("Could not serialize preprocessed features to dict; omitting from response.")
        except Exception as e:
            # Do not fail the extraction; log and continue with None
            logger.warning(f"Preprocessing failed or unavailable: {e}")

    return response
