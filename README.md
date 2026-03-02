## Smart Energy Monitoring System (SEMS) – Hybrid ML & IoT

The **Smart Energy Monitoring System (SEMS)** is a capstone project that implements a **hybrid energy monitoring and management system** that combines:

- **Unsupervised clustering (K‑Means)** to classify household load patterns into NORMAL, HIGH_LOAD, and OVERLOAD.
- **LSTM-based forecasting** to learn temporal patterns of power consumption.
- **Reinforcement Learning (Q‑Learning)** to learn optimal actions (NORMAL / SHIFT / REDUCE) under different load levels.
- An **IoT simulation pipeline using Node‑RED**, which publishes sub‑meter readings to the backend.
- A **Flask web dashboard** that visualizes live data, historical trends, and energy‑saving recommendations.

All components work together to demonstrate **intelligent, closed‑loop energy monitoring and control**.

---

## 1. Project Structure

At a high level, the repository is organized as follows:

- **`app.py`** – Flask backend (REST APIs + web UI routes).
- **`hybrid_model/`**
  - `hybrid_model_training_code.py` – end‑to‑end training pipeline (clustering + LSTM + Q‑Learning) that produces the hybrid model bundle.
- **`models/`**
  - `full_hybrid_energy_model.pkl` – serialized bundle containing the K‑Means model, LSTM, scaler, Q‑table, and auxiliary metadata (created by the training script).
- **`templates/`** – Jinja2 HTML templates used by the Flask app:
  - `base.html` – shared layout (navbar, base styles).
  - `dashboard.html` – main real‑time monitoring dashboard.
  - `devices.html` – device category view (kitchen, HVAC, laundry, electronics).
  - `device_detail.html` – per‑device detail page.
  - `energy_recommendations.html` – insights & saving tips.
  - `profile.html` – user profile / account view.
- **`docs/`**
  - `architecture.md` – detailed system architecture and data flow.
  - `models_and_algorithms.md` – documentation for clustering, LSTM, and Q‑Learning components.
  - `iot_and_nodered.md` – description of the IoT pipeline and Node‑RED flows.
  - `api_reference.md` – HTTP API documentation for the Flask backend.

> Note: the `venv/` directory (Python virtual environment) is intentionally kept separate and is **not** part of the logical project structure.

---

## 2. Dataset

The project uses the **Individual Household Electric Power Consumption** dataset from the UCI Machine Learning Repository [`link`](https://archive.ics.uci.edu/dataset/235/individual+household+electric+power+consumption) (Hebrail & Berard, 2006). This dataset contains **2,075,259** one‑minute sampled measurements collected from a single household in Sceaux, France, between December 2006 and November 2010.

- **Type**: Multivariate, time‑series.
- **Instances**: 2,075,259.
- **Features** (9 core variables):
  - `Date`, `Time`
  - `Global_active_power`, `Global_reactive_power`
  - `Voltage`, `Global_intensity`
  - `Sub_metering_1`, `Sub_metering_2`, `Sub_metering_3`
- **Usage in this project**:
  - `Global_active_power`, `Voltage`, and `Global_intensity` are transformed into **power, voltage, current**.
  - An `hour` feature is derived from `Date`/`Time`.
  - The sub‑metering fields are reinterpreted as IoT‑style sub‑meters (kitchen, laundry, etc.) for simulation.

For local use, the raw file is downloaded and saved as `household_power_consumption.txt` in the project directory, and all preprocessing steps are implemented in `hybrid_model/hybrid_model_training_code.py`.

---

## 3. Technical Overview

- **Backend framework**: Flask (Python).
- **ML stack**:
  - `scikit‑learn` – K‑Means clustering.
  - `TensorFlow / Keras` – LSTM sequence model.
  - `NumPy`, `Pandas` – data handling & feature engineering.
- **RL algorithm**: tabular **Q‑Learning** with a small discrete state/action space.
- **Data source**: `household_power_consumption.txt` preprocessed into IoT‑style features (`power`, `voltage`, `current`, `hour`, sub‑meter readings).
- **IoT simulation**: Node‑RED injects or transforms power data and sends JSON payloads to the Flask backend.
- **Frontend**: HTML templates with JavaScript (fetch API) to poll Flask endpoints and render live dashboards.

For detailed diagrams and deeper explanations, see:

- `docs/architecture.md`
- `docs/models_and_algorithms.md`
- `docs/iot_and_nodered.md`

---

## 4. Running the Project

### 4.1. Prerequisites

- Python 3.10+ (project developed/tested on a modern CPython with TensorFlow support).
- `pip` for dependency management.
- Optional but recommended: create and activate a **virtual environment** (`venv/`).
- Node‑RED installed locally (e.g. via `npm install -g node-red`) for IoT simulation.

### 4.2. Install Dependencies

From the project root:

```bash
pip install -r requirements.txt
```

> If `requirements.txt` does not exist yet, generate it from your environment using `pip freeze > requirements.txt`.

### 4.3. Train the Hybrid Model (Offline Step)

The training step reads `household_power_consumption.txt`, performs:

1. **Feature engineering** (power, voltage, current, hour, sub‑metering).
2. **K‑Means clustering** (3 clusters).
3. **LSTM training** for short‑term power forecasting.
4. **Q‑Learning** over synthetic episodes derived from the observed power distribution.
5. Packaging all artefacts into a single pickle bundle.

Run:

```bash
cd hybrid_model
python hybrid_model_training_code.py
```

Output:

- A `models/full_hybrid_energy_model.pkl` file created in the project root.
- Console printout of the learned hourly average baseline from the LSTM.

### 4.4. Start the Flask Backend

From the project root:

```bash
python app.py
```

The Flask app starts on `http://0.0.0.0:5000` (port 5000).

Core routes:

- `GET /` – web dashboard.
- `GET /devices` – overview of device categories.
- `GET /device/<name>` – per‑category device view.
- `GET /recommendations` – energy recommendation page.
- `GET /profile` – profile page.
- `GET /health` – health check endpoint.

API routes (consumed by Node‑RED and UI):

- `POST /predict` – classify the current sub‑meter readings into NORMAL / HIGH_LOAD / OVERLOAD.
- `POST /node-red-input` – ingest the latest IoT measurement (called by Node‑RED).
- `GET /api/latest` – return the latest ingested measurement.
- `GET /api/history/<submeter>` – 1‑hour history for a given sub‑meter (minute‑bucketed averages).
- `GET /api/history_full` – last 5 ingested records (for table views).

---

## 5. Node‑RED & IoT Simulation

The project integrates with **Node‑RED** to simulate a real IoT deployment:

- Node‑RED flows emulate **smart meter** and **sub‑meter** readings (e.g., `sub_kitchen`, `sub_hvac`, `sub_laundry`, `sub_electronics`).
- These flows periodically send JSON payloads to the backend’s `/node-red-input` endpoint.
- Optionally, you can wire Node‑RED to call `/predict` for every new measurement and visualize the returned **status** or **cluster** on the Node‑RED dashboard.

Example payload sent from Node‑RED to `/node-red-input`:

```json
{
  "sub_kitchen": 350.0,
  "sub_hvac": 1200.0,
  "sub_laundry": 0.0,
  "sub_electronics": 400.0,
  "status": "HIGH_LOAD",
  "severity": "WARNING"
}
```

These records are stored in memory (`ENERGY_STORE`) and served to the dashboard via `/api/latest` and `/api/history*` endpoints.

For full design details of the flows and recommended Node‑RED nodes, see `docs/iot_and_nodered.md`.

---

## 6. Dashboard & Visualization

The Flask dashboard pulls live and recent data from the backend and shows:

- **Current sub‑meter readings** (kitchen, HVAC, laundry, electronics).
- **Load status** (NORMAL / HIGH_LOAD / OVERLOAD) as returned by the clustering model.
- **Short‑term history charts** for each sub‑meter over the last hour.
- **Recent events table** (based on `/api/history_full`).
- **Energy recommendations** derived from the RL policy and simple rule engine.

The HTML templates (`templates/*.html`) are written using **Jinja2** and standard web technologies (HTML, CSS, JavaScript).

---

## 7. Models in Detail

The capstone combines **three core models/techniques**:

- **Clustering (K‑Means)**:
  - Input features: `power`, `voltage`, `current`, `hour`.
  - 3 clusters corresponding to coarse load regimes.
  - At runtime, the backend computes a **cluster ID** from a 4‑dimensional feature vector and maps it to semantic labels: NORMAL, HIGH_LOAD, OVERLOAD.

- **LSTM**:
  - Trained on the `power` time series with a sliding window.
  - Learns short‑term temporal dependencies to predict the next power value.
  - Used offline to derive **hourly baseline loads** for comparison and reporting.

- **Reinforcement Learning (Q‑Learning)**:
  - States: LOW / MEDIUM / HIGH (discretized by power level).
  - Actions: NORMAL / SHIFT / REDUCE.
  - Reward function encourages **load reduction under high demand** and penalizes doing nothing when overloaded.
  - Produces a `Q_table` and `actions` list used to inform recommendation logic.

For mathematical details and training configuration, see `docs/models_and_algorithms.md`.

---

## 8. Extending the Project

Ideas for future work:

- Replace the in‑memory `ENERGY_STORE` with a persistent database (e.g., PostgreSQL, InfluxDB, or TimescaleDB).
- Deploy the Flask app behind a production web server (e.g., gunicorn + Nginx).
- Enrich Node‑RED flows with **real sensor feeds** (e.g., MQTT from esp8266/esp32 devices).
- Implement bi‑directional control loops where the backend sends **control signals** back to IoT devices via Node‑RED based on RL decisions.
- Add more advanced forecasting models (Prophet, temporal fusion transformers, etc.).

---

## 9. Summary

The Smart Energy Monitoring System demonstrates a **complete pipeline** for smart energy monitoring and management:

- A **hybrid ML and RL core** (K‑Means + LSTM + Q‑Learning),
- An **IoT ingestion layer** using Node‑RED,
- And a **real‑time web dashboard** for monitoring and decision support.

The provided source code, architecture diagrams, and documentation are intended to make it straightforward to **reproduce, understand, and extend** this system.

# Smart-energy-monitoring-system
