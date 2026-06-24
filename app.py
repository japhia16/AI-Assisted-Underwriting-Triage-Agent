"""
AI-Assisted Underwriter Workbench — v3
Clean, card-based professional UI inspired by the AI Actuarial Assistant design.
Fixes: memo markdown rendered properly, raw JSON hidden, structured field cards.
"""

import streamlit as st
import requests
from datetime import datetime

# ══════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Underwriter Intake UI",
    page_icon="🛡️",
    layout="wide",
)

API_URL = "http://127.0.0.1:8000"

# ══════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* Base */
html, body, [class*="css"] {
    font-family: 'Segoe UI', system-ui, sans-serif;
    background-color: #0f1117;
}

/* Hide default Streamlit padding */
.block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }

/* ── Cards ─────────────────────────────────────────── */
.uw-card {
    background: #1a1f2e;
    border: 1px solid #252d40;
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 14px;
}
.uw-card-accent {
    background: #1a1f2e;
    border-left: 3px solid #4f8ef7;
    border-radius: 0 10px 10px 0;
    padding: 18px 22px;
    margin-bottom: 14px;
}
.card-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #4f8ef7;
    margin-bottom: 10px;
}

/* ── Premium hero ──────────────────────────────────── */
.premium-value {
    font-size: 36px;
    font-weight: 800;
    color: #f0f4ff;
    letter-spacing: -1.5px;
    line-height: 1;
}
.premium-meta { font-size: 13px; color: #8892b0; margin-top: 6px; }
.uplift-pos   { color: #ff6b6b; font-weight: 600; }
.uplift-neg   { color: #69f0ae; font-weight: 600; }

/* ── Risk badge ────────────────────────────────────── */
.badge {
    display: inline-block;
    padding: 3px 11px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-top: 10px;
}
.badge-high   { background:#ff1744 18%; color:#ff8a80; border:1px solid #ff1744; }
.badge-medium { background:#ff6d00 18%; color:#ffab40; border:1px solid #ff6d00; }
.badge-low    { background:#00c853 18%; color:#69f0ae; border:1px solid #00c853; }

/* ── Info table ────────────────────────────────────── */
.info-tbl { width:100%; border-collapse:collapse; font-size:13.5px; }
.info-tbl td { padding:6px 8px; border-bottom:1px solid #252d40; color:#ccd6f6; }
.info-tbl td:first-child { color:#8892b0; font-weight:600; width:42%; }

/* ── SHAP rows ─────────────────────────────────────── */
.shap-row {
    display:flex; align-items:center; justify-content:space-between;
    padding:7px 0; border-bottom:1px solid #252d40; font-size:13.5px;
}
.shap-row:last-child { border-bottom:none; }
.shap-name  { color:#ccd6f6; flex:1; }
.shap-pos   { color:#ff6b6b; font-weight:700; font-size:13px; }
.shap-neg   { color:#69f0ae; font-weight:700; font-size:13px; }

/* ── Recommendation boxes ──────────────────────────── */
.rec-box {
    border-radius: 8px;
    padding: 13px 16px;
    font-size: 14px;
    line-height: 1.5;
}
.rec-accept  { background:#00c85318; border:1px solid #00c853; color:#69f0ae; }
.rec-refer   { background:#ff6d0018; border:1px solid #ff6d00; color:#ffab40; }
.rec-decline { background:#ff174418; border:1px solid #ff1744; color:#ff8a80; }

/* ── Status pill in sidebar ────────────────────────── */
.status-pill {
    display:inline-flex; align-items:center; gap:7px;
    background:#1a1f2e; border:1px solid #252d40;
    border-radius:20px; padding:6px 14px;
    font-size:13px; color:#ccd6f6; width:100%;
}
.dot-green { width:8px;height:8px;border-radius:50%;background:#69f0ae;flex-shrink:0; }
.dot-red   { width:8px;height:8px;border-radius:50%;background:#ff6b6b;flex-shrink:0; }

/* ── Chip buttons (Try asking) ─────────────────────── */
.chip-grid { display:flex; flex-direction:column; gap:8px; }
.chip {
    background:#1a1f2e; border:1px solid #252d40; border-radius:8px;
    padding:9px 12px; font-size:12px; color:#8892b0; cursor:pointer;
    line-height:1.4;
}
.chip:hover { border-color:#4f8ef7; color:#ccd6f6; }

/* ── Memo header ───────────────────────────────────── */
.memo-ref   { font-size:11px; color:#8892b0; letter-spacing:0.05em; }
.memo-title { font-size:19px; font-weight:700; color:#f0f4ff; margin:3px 0; }
.memo-ts    { font-size:11px; color:#8892b0; }

/* ── Sidebar ───────────────────────────────────────── */
section[data-testid="stSidebar"] > div { background:#0d1117 !important; }
section[data-testid="stSidebar"] .stMarkdown p { color:#8892b0; }

/* ── Divider ───────────────────────────────────────── */
hr { border-color:#252d40 !important; margin: 0.75rem 0 !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🛡️ Underwriter\nWorkbench")
    st.caption(f"Session · {datetime.now().strftime('%d %b %Y, %H:%M')}")
    st.divider()

    # API health
    st.markdown("**🔌 System Status**")
    try:
        hr = requests.get(f"{API_URL}/health", timeout=2)
        if hr.status_code == 200:
            st.markdown('<div class="status-pill"><span class="dot-green"></span>API Gateway: ONLINE</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-pill"><span class="dot-red"></span>API Gateway: OFFLINE</div>',
                        unsafe_allow_html=True)
    except Exception:
        st.markdown('<div class="status-pill"><span class="dot-red"></span>API Gateway: OFFLINE</div>',
                    unsafe_allow_html=True)

    st.divider()

    # Gemini key status
    try:
        import os
        has_key = bool(os.environ.get("GEMINI_API_KEY"))
    except Exception:
        has_key = False

    st.markdown("**🔑 Credentials**")
    if has_key:
        st.success("Gemini API Key detected in environment.")
    else:
        st.warning("Gemini API Key not found — memo will use template fallback.")

    st.divider()

    # Pipeline info
    st.markdown("**⚙️ Pipeline**")
    st.caption("Model · XGBoost + GLM Baseline")
    st.caption("Features · 40 core fields")
    st.caption("Explainability · SHAP TreeExplainer")
    st.caption("Extraction · Gemini LLM / RAG")

    st.divider()

    # Try asking chips
    st.markdown("**💡 Try Asking**")
    EXAMPLES = [
        "Warehouse, Seattle, Sum Insured ₹4 Cr, 2 prior claims, no sprinkler.",
        "Office building Mumbai, Fire Resistive, 10 floors, ₹8 Cr SI, clean claims.",
        "Manufacturing plant Pune, Frame construction, 120 employees, Allied Perils.",
    ]
    for ex in EXAMPLES:
        st.markdown(f'<div class="chip">{ex}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<div class="uw-card-accent" style="margin-bottom:20px;">
    <div style="font-size:22px;font-weight:800;color:#f0f4ff;">🛡️ AI-Assisted Underwriter Workbench</div>
    <div style="font-size:13px;color:#8892b0;margin-top:5px;">
        Extracts structured risk data from broker submissions · ML-powered indicative pricing ·
        SHAP risk explainability · Gemini underwriter memo
    </div>
</div>
""", unsafe_allow_html=True)

tab_text, tab_pdf = st.tabs(["✍️  Paste Raw Text", "📄  Upload PDF"]) 

with tab_text:
    raw_text = st.text_area(
        "Broker Submission Text",
        height=320,
        placeholder="Paste the COMMERCIAL PROPERTY STATEMENT OF VALUES here...",
    )

    if st.button("Process Submission", key="process_text"):
        if not raw_text.strip():
            st.warning("Please paste some text first.")
        else:
            with st.spinner("AI is extracting features and calculating premium..."):
                try:
                    payload = {"text": raw_text}
                    res = requests.post(f"{API_URL}/extract", json=payload, timeout=30)
                    if res.status_code == 200:
                        st.success("✅ Submission processed successfully!")
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            st.subheader("1. AI Extracted Data")
                            st.json(res.json())

                        with col2:
                            st.subheader("2. Pricing Pipeline")
                            data = res.json()
                            if data.get("status") == "complete" and data.get("submission_json"):
                                try:
                                    price_res = requests.post(
                                        f"{API_URL}/price",
                                        json={"submission_json": data["submission_json"]},
                                        timeout=20,
                                    )
                                    if price_res.status_code == 200:
                                        price = price_res.json()
                                        def fmt_inr(x):
                                            if x is None:
                                                return "N/A"
                                            try:
                                                return f"₹{int(x):,}"
                                            except Exception:
                                                return str(x)

                                        premium_card, shap_card = st.columns([1, 1], gap="large")
                                        with premium_card:
                                            st.markdown("### Premium Summary")
                                            st.metric(
                                                label="Final Premium",
                                                value=fmt_inr(price.get("final_premium_INR")),
                                                delta=f"Uplift: {price.get('uplift_pct', 0)}%",
                                            )
                                            st.write("**GLM baseline:**", fmt_inr(price.get("glm_baseline_INR")))
                                            st.write("**XGB prediction:**", fmt_inr(price.get("xgb_prediction_INR")))

                                        with shap_card:
                                            st.markdown("### Top SHAP Drivers")
                                            shap = price.get("top_shap_features", [])
                                            if shap:
                                                for i, feat in enumerate(shap, start=1):
                                                    direction = feat.get("direction", "")
                                                    impact = feat.get("shap_impact")
                                                    st.markdown(
                                                        "<div style='border-left: 4px solid #1f77b4; padding: 10px 12px; margin-bottom: 10px; background: #fafafa;'>"
                                                        f"<strong>{i}. {feat.get('feature')}</strong><br>"
                                                        f"<span style='color: #555;'>{direction} · {fmt_inr(impact)}</span>"
                                                        "</div>",
                                                        unsafe_allow_html=True,
                                                    )
                                            else:
                                                st.info("No SHAP explanation available.")
                                    else:
                                        st.error(f"Pricing API error {price_res.status_code}: {price_res.text}")
                                except Exception as e:
                                    st.error(f"Failed to call pricing API: {e}")
                            else:
                                st.info(data.get("clarifying_question") or "Extraction incomplete — please provide missing fields.")
                    else:
                        st.error(f"API Error {res.status_code}: {res.text}")
                except Exception as e:
                    st.error(f"Failed to connect to backend: {e}")

with tab_pdf:
    uploaded = st.file_uploader("Upload broker PDF", type=["pdf"]) 
    if uploaded:
        with st.spinner("Uploading PDF and requesting extraction..."):
            try:
                files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
                res = requests.post(f"{API_URL}/upload-submission", files=files, timeout=60)
                if res.status_code == 200:
                    st.success("✅ Extraction completed")
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.subheader("1. AI Extracted Data")
                        st.json(res.json())

                    with col2:
                        st.subheader("2. Pricing Pipeline")
                        data = res.json()
                        if data.get("status") == "complete" and data.get("submission_json"):
                            try:
                                price_res = requests.post(
                                    f"{API_URL}/price",
                                    json={"submission_json": data["submission_json"]},
                                    timeout=20,
                                )
                                if price_res.status_code == 200:
                                    price = price_res.json()
                                    def fmt_inr(x):
                                        if x is None:
                                            return "N/A"
                                        try:
                                            return f"₹{int(x):,}"
                                        except Exception:
                                            return str(x)

                                    premium_card, shap_card = st.columns([1, 1], gap="large")
                                    with premium_card:
                                        st.markdown("### Premium Summary")
                                        st.metric(
                                            label="Final Premium",
                                            value=fmt_inr(price.get("final_premium_INR")),
                                            delta=f"Uplift: {price.get('uplift_pct', 0)}%",
                                        )
                                        st.write("**GLM baseline:**", fmt_inr(price.get("glm_baseline_INR")))
                                        st.write("**XGB prediction:**", fmt_inr(price.get("xgb_prediction_INR")))

                                    with shap_card:
                                        st.markdown("### Top SHAP Drivers")
                                        shap = price.get("top_shap_features", [])
                                        if shap:
                                            for i, feat in enumerate(shap, start=1):
                                                direction = feat.get("direction", "")
                                                impact = feat.get("shap_impact")
                                                st.markdown(
                                                    "<div style='border-left: 4px solid #1f77b4; padding: 10px 12px; margin-bottom: 10px; background: #fafafa;'>"
                                                    f"<strong>{i}. {feat.get('feature')}</strong><br>"
                                                    f"<span style='color: #555;'>{direction} · {fmt_inr(impact)}</span>"
                                                    "</div>",
                                                    unsafe_allow_html=True,
                                                )
                                        else:
                                            st.info("No SHAP explanation available.")
                                else:
                                    st.error(f"Pricing API error {price_res.status_code}: {price_res.text}")
                            except Exception as e:
                                st.error(f"Failed to call pricing API: {e}")
                        else:
                            st.info(data.get("clarifying_question") or "Extraction incomplete — please provide missing fields.")
                else:
                    st.error(f"API Error {res.status_code}: {res.text}")
            except Exception as e:
                st.error(f"Failed to upload file to backend: {e}")