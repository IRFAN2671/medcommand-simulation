MedCommand — Hospital Emergency Operations Center

> AI-Powered Hospital Emergency Simulation, Machine Learning Wait-Time Prediction, and Professional Real-Time Dashboard

A complete university final-year project combining **discrete-event simulation**, **dynamic machine learning**, **SQLite audit logging**, and a **professional Streamlit dashboard** with light/dark theme switching.

---

## Features

| Module | Description |
|--------|-------------|
| **📡 Live Operations**   | Real-time KPIs, queue trend, department load, activity feed, doctor status |
| **🏥 Queue & Doctors**   | Doctor panel with status/utilization, priority-color queue, performance charts |
| **🤖 ML Predictions**    | Dynamic RF/XGBoost/DT competition, live wait prediction, feature importance |
| **📊 Resource Center**   | Bed occupancy, peak-hours heatmap, department workload, utilization timeline |
| **🚨 Incident Mgmt**    | MCE trigger, emergency spike, incident timeline, critical surge detection |
| **🗄 Database & Audit** | Searchable/filterable real-time audit log, SQLite persistence, event stats |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. (Optional) Pre-train ML models

```bash
# Windows
set PYTHONPATH=src && python train.py

# Linux / macOS
PYTHONPATH=src python train.py
```

> The dashboard also trains models live during simulation — pre-training is optional.

### 3. Launch the dashboard

```bash
streamlit run app.py
```

Or on Windows, double-click **`run.bat`**.  
Open **http://localhost:8501** → click ** Start** in the sidebar.

---

## Project Structure

```
medcommand/
├── app.py                            # Main Streamlit dashboard (6 tabs, 2 themes)
├── train.py                          # CLI: train RF / XGBoost / DT models
├── predict.py                        # CLI: predict wait time from saved models
├── run.bat / run.sh                  # One-click launchers
├── requirements.txt
│
├── app/
│   ├── config.py                     # All settings in one place
│   ├── state.py                      # Streamlit session state management
│   └── styles.py                     # Dark / light CSS theme system
│
├── src/hospital_sim/
│   ├── simulation/
│   │   └── engine.py                 # HospitalSimulation: tick engine, MCE, spike
│   ├── ml/
│   │   ├── predictor.py              # DynamicMLPredictor: live retrain, competition
│   │   ├── trainer.py                # WaitTimeModelTrainer: offline training
│   │   ├── saved_predictor.py        # WaitTimePredictor: loads .pkl models
│   │   └── evaluation.py             # Model comparison table, leaderboard HTML
│   ├── database/
│   │   ├── db.py                     # SQLite database layer (WAL mode)
│   │   └── logger.py                 # AuditLogger: in-memory + optional SQLite
│   └── utils/
│       └── helpers.py                # Utility functions
│
├── data/
│   ├── medcommand.db                 # SQLite (auto-created at runtime)
│   └── processed/training_data.csv   # Generated training data (auto-created)
│
├── models/                           # Saved .pkl model artifacts
│   ├── random_forest.pkl
│   ├── xgboost.pkl
│   ├── decision_tree.pkl
│   └── metadata.json
│
└── tests/unit/
    ├── test_simulation_engine.py
    ├── test_ml_models.py
    └── test_database.py
```

---

## Usage

### Dashboard

1. Open **http://localhost:8501**
2. Configure doctors (2–5) and arrival rate in the sidebar
3. Press **▶ Start** — dashboard auto-refreshes every 2.5 seconds
4. Trigger **Mass Casualty Events** or **Emergency Spikes** from sidebar
5. Toggle **🌙 Dark theme** for dark mode
6. Monitor all 6 tabs live

### CLI — Train Models

```bash
PYTHONPATH=src python train.py
PYTHONPATH=src python train.py --regenerate-data --runs 80 --ticks 800
```

### CLI — Predict Wait Time

```bash
# Single prediction
PYTHONPATH=src python predict.py --queue 4 --priority 0 --doctors 3 --arrival 0.30

# Compare all models
PYTHONPATH=src python predict.py --queue 4 --priority 1 --doctors 4 --arrival 0.25 --compare
```

Priority codes: `0` = Critical, `1` = Urgent, `2` = Normal

### Run Unit Tests

```bash
PYTHONPATH=src python tests/unit/test_simulation_engine.py
PYTHONPATH=src python tests/unit/test_ml_models.py
PYTHONPATH=src python tests/unit/test_database.py
```

---

## Architecture

```
Streamlit Dashboard (app.py)
        │
        ├── HospitalSimulation (tick engine)          [simulation/engine.py]
        │       ├── Dynamic patient arrivals (sine wave + random spikes)
        │       ├── Priority queue (Critical > Urgent > Normal)
        │       ├── Doctor state machine (Available/Busy/Break/Emergency)
        │       ├── Mass Casualty Event trigger
        │       └── Emergency patient surge trigger
        │
        ├── DynamicMLPredictor                        [ml/predictor.py]
        │       ├── Random Forest   (varies with noise)
        │       ├── XGBoost         (can beat RF on low noise)
        │       ├── Decision Tree   (simpler, overfit risk)
        │       ├── Auto-retrain every 8 ticks
        │       └── Live feature importance tracking
        │
        ├── AuditLogger                               [database/logger.py]
        │       ├── In-memory log (up to 2,000 entries)
        │       ├── Optional SQLite persistence
        │       └── Filter/search/sort API
        │
        └── SimulationDatabase                        [database/db.py]
                ├── patients, doctors, simulation_logs
                ├── ml_predictions, incidents, simulation_runs
                └── WAL-mode SQLite for concurrent reads
```

---

## Configuration

All settings are in `app/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `DEFAULT_NUM_DOCTORS` | 5 | Starting doctor count |
| `DEFAULT_ARRIVAL_RATE` | 0.30 | Base patient arrival probability |
| `DEFAULT_SIM_SPEED` | 2.5s | Seconds between auto-refresh |
| `TICKS_PER_REFRESH` | 3 | Simulation ticks per Streamlit cycle |
| `ML_RETRAIN_EVERY_TICKS` | 8 | How often ML models retrain |
| `ML_TRAINING_RUNS` | 60 | Sim runs for training data generation |

---

## Design Decisions

- **Dynamic arrival rate**: sinusoidal time-of-day pattern + random 10% spike chance
- **Dynamic ML competition**: XGBoost can beat RF under low noise; DT degrades under high queue
- **Feature importance shifts**: queue pressure changes which features matter most
- **No hardcoded results**: every simulation run produces different outcomes
- **WAL-mode SQLite**: smooth concurrent reads during live simulation
- **Fragment-based refresh**: Streamlit ≥ 1.33 uses `@st.fragment` for smooth updates

---

 Academic Notes

- Primary focus: simulation engine as a realistic ED model
- ML is trained on simulation-generated data (supervised, regression)
- Database layer demonstrates WAL-mode SQLite with batched writes
- All modules are independently testable (unit tests provided)

---

**License:** Academic / Educational Use — University Simulation & Modeling Project   
