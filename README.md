# AI-Driven Bike Fleet Relocation System

End-to-end Machine Learning and operational analytics system for predicting daily bike station risk and supporting bike fleet relocation decisions in a smart city environment.

## Live Application

Streamlit Cloud: https://robert-basinski-system-relokacji.streamlit.app/

## Application Preview

### Operational Dashboard

![Operational Dashboard](docs/screenshots/dashboard-main.png)

### Operational Plan KPIs

![Operational Plan KPIs](docs/screenshots/operational-plan-kpis.png)

### Microzone Operations

![Microzone Operations](docs/screenshots/microzone-operational-table.png)

### Station Map View

![Station Map View](docs/screenshots/station-map-view.png)

### Driver Card Module

![Driver Card Module](docs/screenshots/driver-card-module.png)

### Execution Status Dashboard

![Execution Status Dashboard](docs/screenshots/execution-status-dashboard.png)

## Project Overview

This project combines:

- Machine Learning risk scoring
- Operational decision support
- Smart city analytics
- Streamlit dashboard application
- Dispatcher operational panel
- Technical station monitoring
- Geospatial visualization with Folium
- Forecast-based bike relocation planning

The system predicts station-level operational risk and supports dispatchers in daily relocation planning.

## Main Features

### Operational Dispatcher Panel

- Daily operational plan
- Station priority ranking
- Risk categorization
- Recommended relocation actions
- Microzone operational view
- Interactive city map
- Driver support card
- Operational status monitoring

### Technical Monitoring Panel

- Station-level diagnostics
- Risk scoring inspection
- Prediction analysis
- Technical validation layer
- Feature-based operational insights

## Machine Learning Workflow

The project includes:

- Data preprocessing pipeline
- Feature engineering
- Anti-leakage validation
- Classification modeling
- Time-based validation
- LightGBM optimization
- Business-oriented evaluation
- Operational deployment layer

## Technology Stack

### Machine Learning & Analytics

- Python
- Pandas
- NumPy
- Scikit-learn
- LightGBM

### Visualization & Application

- Streamlit
- Folium
- Plotly
- Matplotlib

### Data & Engineering

- Parquet
- Jupyter Notebook
- GitHub
- Streamlit Cloud

### Data & Engineering

- Parquet
- Jupyter Notebook
- GitHub
- Streamlit Cloud

## How to Run Locally

```bash
git clone https://github.com/robert-basinski/system-relokacji-rowerow.git
cd system-relokacji-rowerow
pip install -r requirements.txt
streamlit run app/app_main.py
```

The application uses prepared model and operational artifacts stored in the repository.

## Repository Structure

```text
app/
├── app_main.py
├── 1_Panel_Dyspozytora.py
└── 2_Panel_Techniczny.py

notebooks/
└── 5_Application_Layer.ipynb

artifacts/
outputs_dzien_stacja/
outputs_panel_dyspozytora/
input_model_package/
```

## Business Goal

The goal of the project is to support operational bike fleet management in urban environments by combining Machine Learning predictions with operational decision-support tools.

## Author

Robert Basiński
