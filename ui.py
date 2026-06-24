import requests
import streamlit as st
import json

# Configuration
API_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="Underwriter Intake UI", page_icon="🛡️", layout="wide")

# Sidebar Health Check
st.sidebar.title("System Status")
try:
    response = requests.get(f"{API_URL}/health", timeout=2)
    if response.status_code == 200:
        st.sidebar.success("🟢 API Gateway: ONLINE")
    else:
        st.sidebar.error("🔴 API Gateway: OFFLINE")
except requests.exceptions.RequestException:
    st.sidebar.error("🔴 API Gateway: OFFLINE")

# Main Interface
st.title("🛡️ AI-Assisted Underwriter Workbench")
st.markdown("Paste a broker submission below to instantly extract structured data and generate an XGBoost-powered pricing quote.")

# Tabs for the UI
tab1, tab2 = st.tabs(["✍️ Paste Raw Text", "📄 Upload PDF (Coming Soon)"])

with tab1:
    raw_text = st.text_area(
        "Broker Submission Text", 
        height=300, 
        placeholder="Paste the COMMERCIAL PROPERTY STATEMENT OF VALUES here..."
    )
    
    if st.button("Process Submission", type="primary"):
        if not raw_text.strip():
            st.warning("Please paste some text first.")
        else:
            with st.spinner("AI is extracting features and calculating premium..."):
                try:
                    # Note: Adjust 'text' to whatever your FastAPI schema expects (e.g., 'content', 'submission_text')
                    payload = {"text": raw_text} 
                    
                    # Assuming your FastAPI endpoint is /extract
                    res = requests.post(f"{API_URL}/extract", json=payload)
                    
                    if res.status_code == 200:
                        st.success("✅ Submission processed successfully!")
                        
                        # Display results in two columns
                        col1, col2 = st.columns([1, 1])

                        with col1:
                            st.subheader("1. AI Extracted Data")
                            st.json(res.json())

                        with col2:
                            st.subheader("2. Pricing Pipeline")
                            data = res.json()
                            if data.get("status") == "complete" and data.get("submission_json"):
                                # Call pricing endpoint
                                try:
                                    price_res = requests.post(f"{API_URL}/price", json={"submission_json": data["submission_json"]}, timeout=20)
                                    if price_res.status_code == 200:
                                        price = price_res.json()

                                        # Professional display
                                        st.markdown("### Final Premium")
                                        final_premium = price.get("final_premium_INR")
                                        uplift = price.get("uplift_pct")
                                        glm_base = price.get("glm_baseline_INR")

                                        # formatted
                                        def fmt_inr(x):
                                            try:
                                                return f"₹{int(x):,}"
                                            except Exception:
                                                return str(x)

                                        st.metric(label="Final Premium (INR)", value=fmt_inr(final_premium), delta=f"Uplift: {uplift}%")
                                        st.caption(f"GLM baseline: {fmt_inr(glm_base)}")

                                        st.markdown("#### Top SHAP Drivers")
                                        shap = price.get("top_shap_features", [])
                                        for i, feat in enumerate(shap, start=1):
                                            direction = feat.get("direction", "")
                                            impact = feat.get("shap_impact")
                                            st.write(f"{i}. **{feat.get('feature')}** — {fmt_inr(impact)} ({direction})")
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

with tab2:
    st.info("PDF extraction is handled by a different microservice. Please use the 'Paste Raw Text' tab for this demo.")
