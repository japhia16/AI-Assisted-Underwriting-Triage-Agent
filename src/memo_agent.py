"""
Underwriter Memo Agent using Agno and Gemini.

This module exposes a stable seam for generating an underwriting memo from the
structured submission data produced by the Intake Agent. It uses Agno when the
library and Gemini API key are available, and falls back to a template-based
memo when not.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv

# Attempt to import Agno and Google Gemini model classes. If the installed
# versions are incompatible (or not present), avoid raising at import time so
# the application and tests can still run using the fallback template.
AGNO_AVAILABLE = True
try:
    from agno.agent import Agent
    from agno.exceptions import InputCheckError
    from agno.guardrails.base import BaseGuardrail
    from agno.models.google import Gemini
except Exception:
    AGNO_AVAILABLE = False

    class Agent:  # pragma: no cover - fallback
        pass

    class InputCheckError(Exception):
        pass

    class BaseGuardrail:
        def check(self, run_input: Any) -> None:  # pragma: no cover - fallback
            return None

        async def async_check(self, run_input: Any) -> None:  # pragma: no cover - fallback
            return None

from src.schemas import MemoResponse, PricingHandoff, GuardrailValidationError

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


class DataIntegrityGuardrail(BaseGuardrail):
    """Guardrail that validates key pricing and underwriting inputs."""

    def check(self, run_input: Any) -> None:
        payload = getattr(run_input, "input", run_input)
        if isinstance(payload, dict):
            pure_premium = payload.get("pure_premium")
        else:
            pure_premium = None

        if pure_premium is None or not isinstance(pure_premium, (int, float)) or pure_premium <= 0:
            # Raise a domain-specific exception that the FastAPI app can catch
            raise GuardrailValidationError(f"pure_premium must be provided and greater than zero (got {pure_premium!r}).")

    async def async_check(self, run_input: Any) -> None:
        self.check(run_input)


def format_pricing_summary(premium: float, min_quote: float, max_quote: float) -> str:
    """Format pricing values into a consistent underwriting summary."""
    def _fmt(value: float) -> str:
        return f"${value:,.2f}"

    premium_text = _fmt(premium)
    return (
        f"Pure premium: {premium_text}. "
        f"Estimated pricing range: {_fmt(min_quote)} to {_fmt(max_quote)}."
    )


def generate_memo_doc(submission: dict, pricing: str, shap_explanation: str, flags: list) -> str:
    """Assemble a professional underwriting memo in a strict 3-section format."""
    lines: List[str] = [
        "# Underwriting Memo\n",
        "## Property Overview\n",
    ]

    overview_items = [
        ("Address", submission.get("property_address", "unknown")),
        ("City", submission.get("location_city", "unknown")),
        ("State", submission.get("location_state", "unknown")),
        ("Occupancy", submission.get("occupancy_type", "unknown")),
        ("Construction", submission.get("construction_type", "unknown")),
        ("Building age", submission.get("building_age", "unknown")),
        ("Coverage", submission.get("sum_insured", "unknown")),
        ("Deductible", submission.get("deductible", "unknown")),
    ]

    lines.extend(f"- {label}: {value}" for label, value in overview_items)
    lines.append("\n## Pricing Indication\n")
    lines.append(pricing or "No pricing indication provided.")
    lines.append("\n## Key Risk Drivers\n")

    if flags:
        lines.extend(f"- {flag}" for flag in flags)
    else:
        lines.append("- No elevated risk drivers identified from the submission data.")

    if shap_explanation:
        lines.append("\n### SHAP Explanation\n")
        lines.append(shap_explanation)

    return "\n".join(lines)


def _derive_recommended_action(handoff: PricingHandoff) -> str:
    # Removed underwriting heuristics to enforce strict architectural boundaries.
    # This function previously returned recommended underwriting actions derived
    # from the submission; such guidance must not be implemented in Student 4's
    # code. Keep a neutral placeholder so downstream underwriters make final
    # binding decisions.
    return "Refer to Underwriter for final binding decision"


def _create_agent() -> Optional[Agent]:
    if GEMINI_API_KEY is None:
        logger.warning("GEMINI_API_KEY is missing; memo generation will use the fallback template.")
        return None

    try:
        return Agent(
            name="Underwriter Assistant",
            model=Gemini(id="gemini-2.0-flash", api_key=GEMINI_API_KEY, temperature=0.0),
            tools=[format_pricing_summary, generate_memo_doc],
            pre_hooks=[DataIntegrityGuardrail()],
            instructions=(
                "You are an underwriting assistant. Format the input into a professional underwriting memo with exactly three sections: "
                "Property Overview, Pricing Indication, and Key Risk Drivers. Do not invent new pricing factors or new underwriting conclusions. "
                "Base your memo only on the supplied submission data, pricing summary, and identified risk flags."
            ),
            markdown=True,
            add_name_to_context=False,
            tool_call_limit=2,
        )
    except Exception as exc:
        logger.warning("Failed to initialize Agno agent: %s", exc)
        return None


def _normalize_agent_output(run_output: Any, handoff: PricingHandoff) -> MemoResponse:
    content = getattr(run_output, "content", None)
    raw_text = None

    if isinstance(content, str):
        raw_text = content.strip()
    elif isinstance(content, dict):
        if "memo" in content:
            return MemoResponse(
                memo=str(content.get("memo", "")).strip(),
                highlights=content.get("highlights", []),
                recommended_action=content.get("recommended_action") or "Refer to Underwriter for final binding decision",
            )
        raw_text = json.dumps(content)
    elif content is not None:
        raw_text = str(content).strip()

    if raw_text is None and isinstance(run_output, str):
        raw_text = run_output.strip()
    if raw_text is None:
        raw_text = ""

    highlights: List[str] = []
    if "missing" in raw_text.lower():
        highlights.append("Potential missing or incomplete underwriting details detected.")

    return MemoResponse(
        memo=raw_text,
        highlights=highlights,
        recommended_action="Refer to Underwriter for final binding decision",
    )


def _generate_memo_with_agno(handoff: PricingHandoff) -> MemoResponse:
    agent = _create_agent()
    if agent is None:
        raise RuntimeError("Agno or Gemini API key unavailable for memo generation")

    run_input = {
        "submission_json": handoff.submission_json.model_dump(),
        "preprocessed_json": handoff.preprocessed_json or {},
        "broker_notes": handoff.broker_notes or "",
        "pure_premium": handoff.pure_premium,
    }

    run_output = agent.run(input=run_input)
    return _normalize_agent_output(run_output, handoff)


def _generate_memo_with_template(handoff: PricingHandoff) -> MemoResponse:
    submission = handoff.submission_json
    pricing_text = "Pricing details are not available in this fallback memo."
    if handoff.pure_premium is not None:
        pricing_text = format_pricing_summary(handoff.pure_premium, handoff.pure_premium * 0.9, handoff.pure_premium * 1.1)

    memo_lines = [
        "# Underwriting Memo\n",
        "## Property Overview\n",
        f"- Address: {submission.property_address or 'unknown'}",
        f"- City: {submission.location_city or 'unknown'}",
        f"- State: {submission.location_state or 'unknown'}",
        f"- Occupancy: {submission.occupancy_type or 'unknown'}",
        f"- Construction: {submission.construction_type or 'unknown'}",
        f"- Building age: {submission.building_age if submission.building_age is not None else 'unknown'}",
        f"- Coverage requested: {submission.sum_insured if submission.sum_insured is not None else 'unknown'}",
        f"- Deductible: {submission.deductible if submission.deductible is not None else 'unknown'}",
        "\n## Pricing Indication\n",
        pricing_text,
        "\n## Key Risk Drivers\n",
    ]

    flags: List[str] = []
    if submission.prior_claims_count:
        flags.append(f"Prior claims count: {submission.prior_claims_count}")
    if submission.sprinkler_system is False:
        flags.append("No sprinkler system installed.")
    if submission.fire_protection is None:
        flags.append("Fire protection details unavailable.")
    if submission.nearby_hazard_notes:
        flags.append(f"Nearby hazards: {submission.nearby_hazard_notes}")

    if flags:
        memo_lines.extend(f"- {flag}" for flag in flags)
    else:
        memo_lines.append("- No immediate risk drivers identified from the available data.")

    if handoff.broker_notes:
        memo_lines.append(f"\nBroker notes: {handoff.broker_notes}")

    return MemoResponse(
        memo="\n".join(memo_lines),
        highlights=["Fallback memo used due to missing Gemini API key or runtime failure."],
        recommended_action="Refer to Underwriter for final binding decision",
    )


def generate_underwriter_memo(handoff: PricingHandoff) -> MemoResponse:
    try:
        return _generate_memo_with_agno(handoff)
    except Exception as exc:
        logger.warning("Underwriter memo generation failed, falling back to static template: %s", exc)
        return _generate_memo_with_template(handoff)
