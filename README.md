# Commercial Property Insurance Quote Recommendation System

An agentic AI system that takes a natural-language property description 
from a customer or broker and returns a risk-based premium quote with a 
plain-English explanation of what drove the price.

## What this system does

A customer types something like:
"What would the premium be for a steel-frame warehouse in Surat 
with a sprinkler system, sum insured 4 crore?"

The system responds with a recommended premium and explains 
exactly why — which risk factors increased it and which reduced it.

## How it works

1. **Intake Agent** (Gemini API) — reads the natural-language request 
   and extracts structured underwriting fields

2. **Preprocessing Pipeline** — applies the same feature engineering 
   and encoding used during model training, ensuring consistency 
   between training data and live inputs

3. **Actuarial Models** (Student 2) — a Poisson GLM predicts expected 
   claim frequency, a Gamma GLM predicts expected claim severity. 
   Frequency × Severity = GLM Pure Premium (the auditable baseline)

4. **XGBoost Model** (Student 3) — captures non-linear risk interactions 
   the GLM misses. Final premium = GLM baseline adjusted by a capped 
   XGBoost uplift (±40% governance rule)

5. **SHAP Explainability** — identifies the top risk drivers for every 
   prediction. Positive SHAP = increases premium. Negative SHAP = 
   reduces premium

6. **Explainability Agent** — translates SHAP values into a plain-English 
   underwriter memo

## Tech stack

- Python, Pandas, NumPy
- statsmodels (Poisson + Gamma GLMs)
- XGBoost, SHAP
- scikit-learn (preprocessing pipeline)
- Google Gemini API (natural language intake)
- Jupyter Notebook (model development)

## Dataset

- Synthetic Indian commercial property submissions (5,000 rows)
- India Catastrophic Risk Dataset — district-level flood, cyclone, 
  rainfall, and earthquake risk scores across 724 Indian districts
- India Disaster Database 2020–2025 (event-level reference)

## Key design principle

The language model (Gemini) handles natural language only. 
All pricing logic lives inside the actuarial and ML models. 
The agent explains and recommends — it never prices.

## Team

Built as a group project — 4 students, each owning one layer 
of the pipeline.

Student 1 — Data cleaning and reusable preprocessing pipeline  
Student 2 — Frequency, severity, and risk score models (GLM)  
Student 3 — XGBoost, SHAP, Pricing Agent, governance rule  
Student 4 — Intake Agent (Gemini API) and natural language interface
