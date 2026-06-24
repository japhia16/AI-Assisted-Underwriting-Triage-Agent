"""
AI-Assisted Underwriter Workbench — Streamlit Frontend
=======================================================
Blueprint implementation covering:
  • Global config + API routing
  • Sidebar health check
  • Dual-tab layout (Raw Text / PDF Upload)
  • Shared extraction-result renderer
  • Pricing display with SHAP risk drivers
"""

import streamlit as st
import requests

# ══════════════════════════════════════════════════════════════════
# 1. GLOBAL APP CONFIGURATION
# ══════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Underwriter Intake UI",
    page_icon="🛡️",
    layout="wide",
)

API_URL = "http://127.0.0.1:8000"


# ══════════════════════════════════════════════════════════════════
# 2. SIDEBAR — SYSTEM HEALTH CHECK
# ══════════════════════════════════════════════════════════════════

with st.sidebar:
    st.title("System Status")
    try:
        health_resp = requests.get(f"{API_URL}/health", timeout=2)
        if health_resp.status_code == 200:
            st.success("🟢 API Gateway: ONLINE")
        else:
            st.error("🔴 API Gateway: OFFLINE")
    except Exception:
        st.error("🔴 API Gateway: OFFLINE")

    st.divider()
    st.markdown("**Pipeline Configuration**")
    st.caption("• Max features: 40 core fields")
    st.caption("• Model: XGBoost + GLM Baseline")
    st.caption("• Explainability: SHAP values")
    st.caption("• Extraction: LLM / RAG layer")


# ══════════════════════════════════════════════════════════════════
# 3. MAIN HEADER & NAVIGATION
# ══════════════════════════════════════════════════════════════════

st.title("🛡️ AI-Assisted Underwriter Workbench")
st.markdown(
    "_Extracts structured data from broker submissions to generate "
    "**ML-powered pricing** using a 40-feature XGBoost pipeline with "
    "GLM baseline adjustment and SHAP-based risk explainability._"
)
st.divider()

tab_text, tab_pdf = st.tabs(["✍️ Paste Raw Text", "📄 Upload PDF"])


# ══════════════════════════════════════════════════════════════════
# SHARED HELPER — PRICING DISPLAY  (Section 5)
# ══════════════════════════════════════════════════════════════════

def render_pricing(submission_json: dict) -> None:
    """
    POST submission_json to /price and render:
      • Final Premium metric  (with Governance Uplift as delta)
      • GLM Baseline
      • SHAP top risk drivers
    """
    try:
        price_resp = requests.post(
            f"{API_URL}/price",
            json={"submission_json": submission_json},
            timeout=30,
        )

        if price_resp.status_code == 200:
            pricing = price_resp.json()

            final_premium      = pricing.get("final_premium_INR", 0)
            governance_uplift  = pricing.get("uplift_pct", 0)
            glm_baseline       = pricing.get("glm_baseline_INR", 0)
            shap_features      = pricing.get("top_shap_features", [])

            # ── Final Premium metric ──────────────────────────────
            st.metric(
                label="🏷️ Final Premium (INR)",
                value=f"₹{final_premium:,.2f}",
                delta=f"{governance_uplift:+.2f}% Governance Uplift",
            )

            # ── GLM Baseline ──────────────────────────────────────
            st.markdown(f"**GLM Baseline:** &nbsp; ₹{glm_baseline:,.2f}")
            st.divider()

            # ── SHAP Risk Drivers ─────────────────────────────────
            st.subheader("📊 Top Risk Drivers (SHAP)")

            if shap_features:
                for feat in shap_features:
                    name   = feat.get("feature", "Unknown")
                    impact = feat.get("shap_impact", 0)
                    arrow  = "🔺" if impact >= 0 else "🔻"
                    sign   = "+" if impact >= 0 else "−"
                    st.markdown(
                        f"{arrow} &nbsp; **{name}** &nbsp;|&nbsp; "
                        f"`{sign}₹{abs(impact):,.2f}`",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No SHAP features returned by the model.")

        elif price_resp.status_code == 500:
            st.error("🔥 Pricing engine returned a 500 error.")
            st.info(
                "💡 **Debug Hint:** XGBoost encountered an issue — likely a missing or "
                "non-numeric field in the extracted JSON. Check the **backend terminal** "
                "for the full traceback and verify all numeric fields are correctly typed "
                "before re-submitting."
            )

        else:
            st.error(f"Pricing API error: HTTP {price_resp.status_code}")
            try:
                st.json(price_resp.json())
            except Exception:
                st.text(price_resp.text)

    except requests.exceptions.RequestException as exc:
        st.error(f"Could not reach the pricing endpoint: {exc}")
        st.info(
            "💡 **Debug Hint:** Ensure the FastAPI backend is running and `/price` is "
            "registered. Check the backend terminal for missing numeric field errors."
        )


# ══════════════════════════════════════════════════════════════════
# SHARED HELPER — EXTRACTION RESULT RENDERER  (Sections 4 & 6)
# ══════════════════════════════════════════════════════════════════

def render_extraction_result(result: dict) -> None:
    """
    Central renderer used by BOTH Tab 1 and Tab 2.

    Handles two status branches returned by /extract or /extract-pdf:
      • "needs_clarification" → warning banner + split view of partial JSON / missing fields
      • "complete"            → success banner + split view of full JSON / pricing output
    """
    status = result.get("status", "")

    # ── Branch A: Needs Clarification ────────────────────────────
    if status == "needs_clarification":
        st.warning("⚠️ **Incomplete Submission** — Clarification Required Before Pricing")
        st.info(
            f"💬 **AI Clarifying Question:**  \n"
            f"{result.get('clarifying_question', 'Please supply the missing details.')}"
        )

        col_partial, col_missing = st.columns(2)

        with col_partial:
            st.subheader("📋 Partially Extracted Data")
            st.json(result.get("submission_json", {}))

        with col_missing:
            st.subheader("🔍 Missing Fields")
            missing_fields = result.get("missing_fields", [])
            if missing_fields:
                for field in missing_fields:
                    st.markdown(
                        f"❌ &nbsp; `{field}`",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No specific missing fields identified.")

    # ── Branch B: Complete ────────────────────────────────────────
    elif status == "complete":
        st.success("✅ **Extraction Complete** — Pricing pipeline engaged.")

        submission_json = result.get("submission_json", {})

        col_json, col_price = st.columns(2)

        with col_json:
            st.subheader("📋 Extracted Submission Data")
            st.json(submission_json)

        with col_price:
            st.subheader("💰 Pricing Engine Output")
            render_pricing(submission_json)

    # ── Fallback: Unknown Status ──────────────────────────────────
    else:
        st.error(
            f"Unexpected API response status: `{status or '(empty)'}`. "
            "Raw payload shown below."
        )
        st.json(result)


# ══════════════════════════════════════════════════════════════════
# 4. TAB 1 — RAW TEXT PROCESSING
# ══════════════════════════════════════════════════════════════════

with tab_text:
    st.subheader("Broker Submission — Raw Text Input")
    st.caption(
        "Paste the full broker submission below. The LLM/RAG extraction layer "
        "caps at 40 core features — spinner resolves in milliseconds."
    )

    raw_text = st.text_area(
        label="Broker Submission Text",
        placeholder=(
            "Paste your broker submission here…\n\n"
            "Example:\n"
            "Insured: ABC Manufacturing Pvt Ltd\n"
            "Location: Plot 45, MIDC, Pune — 411018\n"
            "Occupancy: Light engineering / metal fabrication\n"
            "Sum Insured (Fire): ₹12,00,00,000\n"
            "Business Interruption: ₹3,50,00,000 (12-month indemnity)\n"
            "Claims History: 1 loss in last 5 years — ₹8,50,000 (machinery breakdown)\n"
            "…"
        ),
        height=300,
    )

    process_text_btn = st.button(
        "⚡ Process Text Submission",
        type="primary",
        key="btn_process_text",
    )

    if process_text_btn:
        if not raw_text.strip():
            st.warning("⚠️ Please paste some broker submission text before processing.")
        else:
            with st.spinner("Extracting features and calculating premium..."):
                try:
                    extract_resp = requests.post(
                        f"{API_URL}/extract",
                        json={"text": raw_text},
                        timeout=60,
                    )
                    if extract_resp.status_code == 200:
                        render_extraction_result(extract_resp.json())
                    else:
                        st.error(
                            f"Extraction API returned HTTP {extract_resp.status_code}."
                        )
                        try:
                            st.json(extract_resp.json())
                        except Exception:
                            st.text(extract_resp.text)

                except requests.exceptions.ConnectionError:
                    st.error(
                        "🔴 Could not connect to the API Gateway. "
                        "Is the FastAPI backend running on port 8000?"
                    )
                except requests.exceptions.Timeout:
                    st.error(
                        "⏱️ Request timed out. The extraction pipeline may be under load — "
                        "try again in a moment."
                    )
                except Exception as exc:
                    st.error(f"Unexpected error: {exc}")


# ══════════════════════════════════════════════════════════════════
# 6. TAB 2 — PDF PROCESSING
# ══════════════════════════════════════════════════════════════════

with tab_pdf:
    st.subheader("Broker Submission — PDF Upload")
    st.caption(
        "Upload a PDF broker submission. The backend will extract raw text, "
        "run the LLM/RAG extraction layer (≤40 features), and feed the result "
        "into the same pricing pipeline as Tab 1."
    )

    uploaded_pdf = st.file_uploader(
        label="Upload Broker Submission PDF",
        type=["pdf"],
        help="Multi-page broker submission PDFs are fully supported.",
    )

    process_pdf_btn = st.button(
        "📄 Process PDF Document",
        type="primary",
        key="btn_process_pdf",
    )

    if process_pdf_btn:
        if uploaded_pdf is None:
            st.warning("⚠️ Please upload a PDF file before processing.")
        else:
            with st.spinner("Extracting features and calculating premium..."):
                try:
                    pdf_bytes = uploaded_pdf.read()

                    extract_resp = requests.post(
                        f"{API_URL}/extract-pdf",
                        files={
                            "file": (
                                uploaded_pdf.name,
                                pdf_bytes,
                                "application/pdf",
                            )
                        },
                        timeout=120,   # PDF parsing warrants a longer timeout
                    )

                    if extract_resp.status_code == 200:
                        # ✅ Reuses the exact same renderer as Tab 1
                        render_extraction_result(extract_resp.json())
                    else:
                        st.error(
                            f"PDF Extraction API returned HTTP {extract_resp.status_code}."
                        )
                        try:
                            st.json(extract_resp.json())
                        except Exception:
                            st.text(extract_resp.text)

                except requests.exceptions.ConnectionError:
                    st.error(
                        "🔴 Could not connect to the API Gateway. "
                        "Is the FastAPI backend running on port 8000?"
                    )
                except requests.exceptions.Timeout:
                    st.error(
                        "⏱️ PDF processing timed out. Large documents may need more time — "
                        "try re-uploading or check the backend terminal."
                    )
                except Exception as exc:
                    st.error(f"Unexpected error: {exc}")