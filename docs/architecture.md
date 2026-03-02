## System Architecture

This document explains the **end‑to‑end architecture** of the Smart Energy Monitoring System (SEMS) and how its components interact.

---

## 1. High‑Level Components

- **Data Source & Preprocessing**
  - Raw dataset: *Individual Household Electric Power Consumption* (`household_power_consumption.txt`), downloaded from the UCI Machine Learning Repository [`link`](https://archive.ics.uci.edu/dataset/235/individual+household+electric+power+consumption).
  - Preprocessing and feature engineering implemented in `hybrid_model/hybrid_model_training_code.py`.

- **Hybrid Analytics Core**
  - **K‑Means clustering** for usage categorization.
  - **LSTM** for time‑series forecasting.
  - **Q‑Learning** for policy learning (optimal actions under different load regimes).
  - Packaged into a single pickle bundle: `models/full_hybrid_energy_model.pkl`.

- **Backend API (Flask) – `app.py`**
  - Hosts ML inference endpoints (`/predict`).
  - Ingests IoT data from Node‑RED (`/node-red-input`).
  - Exposes REST APIs (`/api/latest`, `/api/history/*`) for the dashboard.
  - Renders HTML templates for the UI (dashboard, devices, recommendations, profile).

- **IoT Simulation (Node‑RED)**
  - Simulates smart meter and sub‑meter readings.
  - Publishes JSON messages to the Flask backend.
  - Optionally reads predictions back and visualizes them on a Node‑RED dashboard.

- **Web Frontend (Flask Templates)**
  - `dashboard.html`, `devices.html`, `device_detail.html`, `energy_recommendations.html`, `profile.html`.
  - Use JavaScript to call backend APIs and update charts/widgets.

---

## 2. Data Flow

### 2.1 Offline Training Flow

1. **Load dataset**
   - Read the downloaded *Individual Household Electric Power Consumption* file (`household_power_consumption.txt`) into a Pandas DataFrame.
   - Parse timestamp (`Date` + `Time`) and convert target numeric columns.

2. **Feature engineering**
   - Compute `power` (from `Global_active_power`), `voltage`, `current`, `hour`.
   - Derive IoT‑style sub‑metering features.

3. **Clustering**
   - Apply **K‑Means (3 clusters)** on selected features.
   - Store cluster assignments and centroids.

4. **LSTM Training**
   - Normalize `power` using `MinMaxScaler`.
   - Create sliding windows for sequence modeling.
   - Train an **LSTM regression model** to predict the next power value.
   - Derive an **hourly average baseline** from LSTM outputs.

5. **Reinforcement Learning (Q‑Learning)**
   - Discretize the power domain into 3 states: LOW, MEDIUM, HIGH.
   - Define actions: NORMAL, SHIFT, REDUCE.
   - Define a reward function that:
     - Rewards REDUCE when in HIGH state.
     - Penalizes staying NORMAL in HIGH state.
     - Gives small positive rewards in other cases.
   - Run Q‑Learning updates over random samples from the empirical power distribution.

6. **Bundle and persist**
   - Save `kmeans`, `lstm_model`, `scaler`, `Q_table`, `actions`, `hourly_lstm_avg` into `models/full_hybrid_energy_model.pkl`.

The output of this phase is a **self‑contained hybrid model bundle** used by the online system.

### 2.2 Online Inference & IoT Flow

1. **Node‑RED IoT Simulation**
   - Generates or transforms readings for:
     - `sub_kitchen`, `sub_hvac`, `sub_laundry`, `sub_electronics`.
   - Optionally also includes:
     - `status` and `severity` (pre‑computed or from `/predict`).
   - Sends a JSON payload to `POST /node-red-input`.

2. **Backend Ingestion (`/node-red-input`)**
   - Reads JSON payload.
   - Enriches with `timestamp`.
   - Appends the record to in‑memory `ENERGY_STORE`.
   - Maintains a fixed size buffer (oldest records dropped after a threshold).

3. **Classification (`/predict`)**
   - Receives a feature vector from Node‑RED or another client.
   - Uses the K‑Means model (`kmeans.predict`) to map the current load to a cluster.
   - Maps cluster ID to semantic labels: NORMAL, HIGH_LOAD, OVERLOAD.
   - Returns JSON with `prediction`, `cluster_id`, and a description of used features.

4. **History & Aggregation**
   - `/api/latest` returns the last ingested record.
   - `/api/history/<submeter>` aggregates the last 1 hour of data into per‑minute averages.
   - `/api/history_full` returns the last 5 records for compact tables.

5. **Frontend & Dashboard**
   - JavaScript on the dashboard polls these APIs.
   - Visual components (cards, charts, tables) render:
     - Current readings
     - Short‑term history
     - Load status
     - Recommendations (using RL policy + rule engine)

---

## 3. Component Responsibilities

- **`hybrid_model_training_code.py`**
  - Owns all **offline analytics**: dataset handling, clustering, LSTM, Q‑Learning.
  - Exposes no HTTP or real‑time interface.
  - Produces the `full_hybrid_energy_model.pkl` bundle.

- **`app.py`**
  - Loads the model bundle once at startup.
  - Offers a clean separation between:
    - **Model inference** (`/predict`).
    - **Data ingestion** (`/node-red-input`).
    - **Aggregation APIs** (`/api/latest`, `/api/history*`).
    - **User interface** (routes rendering templates).

- **Node‑RED**
  - Emulates an **edge layer** of devices and gateways.
  - Decouples sensor simulation and pipes data into the backend over HTTP.
  - Can also display prediction results and control signals.

- **Templates**
  - Implement the **presentation layer**.
  - Contain no business logic beyond simple conditional rendering and loops.

---

## 4. Deployment View

- **Local development**
  - Run `python hybrid_model_training_code.py` once to create/update the model bundle.
  - Start Flask with `python app.py`.
  - Start Node‑RED and configure flows to point to `http://localhost:5000`.

- **Potential production deployment**
  - Run the Flask app behind a WSGI server (gunicorn, uWSGI).
  - Front with a reverse proxy (Nginx / Apache).
  - Replace in‑memory storage with a time‑series database.
  - Host Node‑RED on the same or a different node, connected over secure network channels.

---

## 5. Summary

The architecture follows a **clear separation of concerns**:

- **Offline ML/RL training** in `hybrid_model/`.
- **Online serving and visualization** in `app.py` + templates.
- **IoT simulation and orchestration** in Node‑RED.

This separation makes the system easier to reason about, maintain, and extend for future research or real deployments.

