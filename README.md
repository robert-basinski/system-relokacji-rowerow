# AI-Driven Bike Fleet Relocation System

![Python](https://img.shields.io/badge/Python-3.12.8-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-Live-red)
![LightGBM](https://img.shields.io/badge/ML-LightGBM-green)
![Status](https://img.shields.io/badge/Status-Production--Style-success)

End-to-end Machine Learning and operational analytics system for predicting daily bike station risk and supporting bike fleet relocation decisions in a smart city environment.

## Live Application

🚴 [Open Live Streamlit Application](https://robert-basinski-system-relokacji.streamlit.app/)

## Application Preview

### Operational Dashboard

<img src="docs/screenshots/dashboard-main.png" width="600">

### Operational Plan KPIs

<img src="docs/screenshots/operational-plan-kpis.png" width="600">

### Microzone Operations

<img src="docs/screenshots/microzone-operational-table.png" width="600">

### Station Map View

<img src="docs/screenshots/station-map-view.png" width="600">

### Driver Card Module

<img src="docs/screenshots/driver-card-module.png" width="600">

### Execution Status Dashboard

<img src="docs/screenshots/execution-status-dashboard.png" width="600">

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

## Project Highlights

- End-to-end ML-powered urban bike fleet management platform
- Real operational dispatcher workflow simulation
- Integrated technical and operational dashboard architecture
- Time-based validation and anti-leakage ML workflow
- LightGBM-based station risk classification
- Geospatial operational monitoring with Folium
- Streamlit production-style application layer
- Operational KPI aggregation and recommendation system
- Multi-layer parquet artifact architecture
- Smart-city operational decision support system

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

### Key Operational Capabilities

- Bike relocation planning and prioritization
- Risk-based station prioritization
- Microzone balancing strategy
- Forecast-supported operational recommendations
- Dispatcher decision support
- Driver execution workflow
- Interactive operational monitoring
- Geospatial operational visualization
- Real-time style operational dashboard
- Operational KPI aggregation

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

## Analytical Documentation Approach

The project intentionally includes extensive analytical markdown documentation inside the notebooks.

Blocks `1_EDA_Preprocessing.ipynb` and `2_Time_Series_Analysis.ipynb` contain detailed step-by-step analytical interpretations, validation comments and operational reasoning attached directly to the code workflow.

The purpose of this approach is to demonstrate:

- analytical thinking process
- interpretation of operational and ML results
- validation-driven workflow
- understanding of data behavior
- business-oriented reasoning
- transparent decision-making process
- technical communication skills

The notebook section titles and selected explanatory comments are written in Polish to keep the analytical narrative clear and natural for the target presentation context. At the same time, the technical code structure, variable naming, data-processing logic and engineering workflow are kept in English, following common programming and Data Science conventions.

The Streamlit application interface is currently written in Polish because the operational scenario is designed for a Polish-speaking dispatcher and driver workflow. The application structure is modular and can be translated to English without changing the underlying ML logic, data pipeline or deployment architecture.

Rather than presenting only raw code execution, the notebooks document how analytical conclusions were reached and how operational decisions were derived from the data.

Blocks `3–6` focus more on compact engineering summaries and production-oriented workflow documentation, while maintaining the same validation-first philosophy across the entire project.

## Project Workflow Blocks

The project is structured into six logical workflow blocks:

| Block | Notebook | Purpose |
|---|---|---|
| 1 | `1_EDA_Preprocessing.ipynb` | Initial data analysis, preprocessing and data quality verification |
| 2 | `2_Time_Series_Analysis.ipynb` | Time series analysis and operational demand patterns |
| 3 | `3_Model_Training.ipynb` | Classification model training for day-station risk prediction |
| 3.1 | `3_1_Model_Optimization.ipynb` | Model optimization, validation and feature selection |
| 4 | `4_Deployment_Pipeline.ipynb` | Deployment pipeline, inference logic and model package preparation |
| 5 | `5_Application_Layer.ipynb` | Streamlit application layer and technical application integration |
| 6 | `6_Dispatcher_System.ipynb` | Dispatcher panel, relocation recommendations and operational decision support |

## Technology Stack

### Core Technologies

- Python 3.12
- Streamlit
- LightGBM
- Pandas
- Scikit-learn
- Folium
- Plotly
- Parquet

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
├── 1_EDA_Preprocessing.ipynb
├── 2_Time_Series_Analysis.ipynb
├── 3_Model_Training.ipynb
├── 3_1_Model_Optimization.ipynb
├── 4_Deployment_Pipeline.ipynb
├── 5_Application_Layer.ipynb
└── 6_Dispatcher_System.ipynb

docs/
├── screenshots/
└── architecture/

config/
├── app_config.json
└── scoring_thresholds.json

artifacts/
├── model artifacts
├── feature screening reports
└── deployment support files

input_model_package/
├── model artifacts
├── inference configuration
└── feature importance outputs

outputs_dzien_stacja/
└── technical scoring outputs for the day-station panel

outputs_panel_dyspozytora/
└── operational dispatcher panel outputs and recommendation layers

app_runtime/
└── runtime predictions, run logs and application execution metadata

requirements.txt
README.md
```

## System Architecture

👉 Full architecture diagram: [View System Architecture](docs/architecture/system_architecture.md)

The project is divided into several operational and Machine Learning layers:

### Data Layer
- Aggregated station analytics
- Operational parquet datasets
- Forecast and weather integration
- Historical station behavior profiles

### Machine Learning Layer
- Feature engineering
- Anti-leakage validation
- Classification modeling
- LightGBM optimization
- Time-based validation

### Operational Layer
- Dispatcher operational planning
- Station prioritization
- Relocation recommendations
- Driver task management
- Execution monitoring

### Application Layer
- Streamlit operational dashboard
- Technical monitoring panel
- Interactive geospatial visualization
- Operational KPI reporting

## Business Goal

The goal of the project is to support operational bike fleet management in urban environments by combining Machine Learning predictions with operational decision-support tools.

## Author

Robert Basiński
