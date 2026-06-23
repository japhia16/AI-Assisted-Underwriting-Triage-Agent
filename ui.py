import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Underwriter Intake UI", page_icon="🛡️", layout="wide")
st.sidebar.title("System Status")

try:
    response = requests.get(f"{API_URL}/health", timeout=2)
    if response.status_code == 200:
        st.sidebar.success("🟢 API Gateway: ONLINE")
    else:
        st.sidebar.error("🔴 API Gateway: OFFLINE")
except requests.exceptions.RequestException:
    st.sidebar.error("🔴 API Gateway: OFFLINE")

st.title("Underwriter Intake UI")
st.markdown("This app checks API health and renders the status in the sidebar.")
