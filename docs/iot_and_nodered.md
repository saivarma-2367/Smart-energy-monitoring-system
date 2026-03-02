## IoT Simulation and Node‑RED

This document explains how the project uses **Node‑RED** to simulate IoT devices and how these flows interact with the Flask backend.

---

## 1. Role of Node‑RED

Node‑RED acts as an **edge layer** that:

- Simulates **smart energy meters** and **sub‑meters** (kitchen, HVAC, laundry, electronics).
- Periodically sends JSON payloads to the backend’s `/node-red-input` endpoint.
- Can optionally call `/predict` to get **load classification** and display it on a Node‑RED dashboard.
- Provides a GUI environment for wiring together flows, inject nodes, dashboards, and HTTP nodes.

---

## 2. Data Model for IoT Messages

Typical fields used in the project:

- `sub_kitchen` – instantaneous or aggregated power for kitchen loads.
- `sub_hvac` – power for HVAC equipment (e.g., AC, fans).
- `sub_laundry` – power for laundry devices (e.g., washing machine).
- `sub_electronics` – power for household electronics (TV, laptop, router, etc.).
- `status` – high‑level classification (e.g., NORMAL, HIGH_LOAD, OVERLOAD).
- `severity` – optional label (e.g., INFO, WARNING, CRITICAL).

Example JSON sent by Node‑RED to `/node-red-input`:

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

The Flask app enriches this with a `timestamp` field and stores it in an in‑memory list (`ENERGY_STORE`).

---

## 3. Core HTTP Endpoints

### 3.1. `/node-red-input` – Ingestion

- **Method**: `POST`
- **Body**: JSON with sub‑meter readings and optional status/severity.
- **Behavior**:
  - Parses the JSON.
  - Attaches `timestamp = datetime.now().isoformat()`.
  - Appends the record to `ENERGY_STORE`.
  - Trims the buffer length (drops oldest entries when a limit is exceeded).

Used primarily by **Node‑RED** to stream IoT data into the backend.

### 3.2. `/predict` – Classification

- **Method**: `POST`
- **Body**: JSON containing a `features` list.
- **Interpretation**:
  - `features = [hour, kitchen, hvac, laundry, electronics, voltage, current]`.
  - The backend extracts sub‑meter values and builds a feature vector for the K‑Means model.
- **Output**:
  - `prediction` – one of `NORMAL`, `HIGH_LOAD`, `OVERLOAD`.
  - `cluster_id` – underlying cluster index (0 / 1 / 2).
  - `used_features` – documentation of the feature order.

Node‑RED can call this endpoint after generating readings in order to:

- Classify the current condition.
- Display the label on its own dashboard.
- Forward `status`/`severity` along with raw readings to `/node-red-input`.

### 3.3. Read APIs Used by the Web Dashboard

While these endpoints are used mainly by the Flask templates and browser JavaScript, they can also be consumed by Node‑RED if needed:

- `GET /api/latest` – returns the most recent record in `ENERGY_STORE`.
- `GET /api/history/<submeter>` – returns minute‑bucketed averages for the last hour.
- `GET /api/history_full` – returns a compact list of the last 5 records.

---

## 4. Example Node‑RED Flow (Conceptual)

Below is a **conceptual** description of how the flows can be wired in Node‑RED.

1. **Inject Node(s)**
   - Generate test readings at a fixed interval (e.g., every 5 seconds).
   - Values can be:
     - Random within realistic ranges, or
     - Derived from a predefined profile.

2. **Function Node – Build Payload**
   - Construct a JavaScript object:

     ```javascript
     msg.payload = {
       sub_kitchen: ...,
       sub_hvac: ...,
       sub_laundry: ...,
       sub_electronics: ...
     };
     return msg;
     ```

3. **HTTP Request Node – Call `/predict` (optional)**
   - Configure as:
     - Method: `POST`
     - URL: `http://localhost:5000/predict`
   - Map `msg.payload` into the `features` array expected by the backend.
   - Parse JSON response to obtain `prediction` and `cluster_id`.

4. **Function Node – Enrich with Status**
   - Attach `status` and `severity` based on the prediction:

     ```javascript
     msg.payload.status = prediction;       // e.g., "HIGH_LOAD"
     msg.payload.severity = "WARNING";      // or based on cluster
     return msg;
     ```

5. **HTTP Request Node – Call `/node-red-input`**
   - Method: `POST`
   - URL: `http://localhost:5000/node-red-input`
   - Send the enriched JSON payload to the backend.

6. **Dashboard Nodes (Node‑RED UI)**
   - Display:
     - Current values (gauges, numeric widgets).
     - Status labels (text panels, color‑coded).
     - Trends (charts based on data polled from Flask or internal Node‑RED variables).

---

## 5. Integration with the Flask Dashboard

The Flask web dashboard and the Node‑RED flows together provide **two perspectives** on the same data:

- **Node‑RED side**
  - Focused on **device‑level simulation** and raw IoT flows.
  - Useful to emulate how sensors and gateways behave.

- **Flask side**
  - Focused on **analytics and visualization**:
    - Live status (NORMAL / HIGH_LOAD / OVERLOAD).
    - History graphs based on `/api/history/<submeter>`.
    - Tables of recent events.
    - Recommendations powered by ML + RL.

Because both sides use HTTP and JSON, they are loosely coupled and easy to extend.

---

## 6. Summary

Node‑RED is used to **simulate and orchestrate IoT data**, while Flask provides the **analytics and visualization layer**. Together they demonstrate how a real‑world smart energy system might be structured:

- Edge devices (simulated by Node‑RED) → Gateway/API (`/node-red-input`) → Analytics (clustering, LSTM, Q‑Learning) → Dashboards and recommendations.

