# Digital Twin Cementing — Level 3 Premium (Hybrid Dark)

This package contains a premium hybrid-dark Streamlit prototype for a Digital Twin of Cementing operations.

Files included:
- app.py  -> main Streamlit application (hybrid dark UI)
- sample_slurries.csv -> example slurry dataset (final)
- requirements.txt -> pinned dependencies

How to deploy locally:
1. unzip, create venv, install requirements, run:
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   streamlit run app.py

How to deploy to Streamlit Cloud:
1. Push files to GitHub repo root (app.py, sample_slurries.csv, requirements.txt)
2. On Streamlit Cloud create New App, choose repo & main file app.py, deploy.

