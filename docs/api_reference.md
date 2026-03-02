## API Reference – Flask Backend

This document describes the HTTP endpoints exposed by the Flask application (`app.py`).

Base URL (development): `http://localhost:5000`

---

## 1. Health Check

### `GET /health`

**Description**: Simple health check to verify that the backend is running.

- **Request body**: none.
- **Response**:

```json
{
  "status": "ok"
}
```

---

## 2. ML Classification

### `POST /predict`

**Description**: Classify the current load into one of the cluster labels: `NORMAL`, `HIGH_LOAD`, or `OVERLOAD`, using the trained K‑Means model.

- **Request body** (JSON):

```json
{
  "features": [
    hour,
    kitchen,
    hvac,
    laundry,
    electronics,
    voltage,
    current
  ]
}
```

Only the sub‑metering entries (`kitchen`, `hvac`, `laundry`, `electronics`) are currently used for clustering inside the endpoint.

- **Successful response** (`200 OK`):

```json
{
  "prediction": "HIGH_LOAD",
  "cluster_id": 1,
  "used_features": [
    "sub_kitchen",
    "sub_hvac",
    "sub_laundry",
    "sub_electronics"
  ]
}
```

- **Error responses**:
  - `400 Bad Request` if `features` is missing or invalid.

---

## 3. IoT Data Ingestion

### `POST /node-red-input`

**Description**: Ingest a new IoT measurement from Node‑RED or another client. Records are stored in memory (`ENERGY_STORE`) with a timestamp.

- **Request body** (JSON):

  Example:

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

- **Behavior**:
  - If the JSON is missing or malformed → `400 Bad Request`.
  - On success:
    - Adds `timestamp` in ISO format.
    - Appends the record to `ENERGY_STORE`.
    - Enforces a maximum history length (oldest entries dropped once a threshold is exceeded).

- **Successful response** (`200 OK`):

```json
{
  "status": "SUCCESS"
}
```

---

## 4. Data Access APIs

### `GET /api/latest`

**Description**: Returns the most recent record ingested via `/node-red-input`.

- **Request body**: none.
- **Response**:
  - If `ENERGY_STORE` is empty: empty JSON `{}`.
  - Otherwise, the last stored record, including:
    - `timestamp`
    - `sub_kitchen`, `sub_hvac`, `sub_laundry`, `sub_electronics` (if present)
    - `status`, `severity` (if present)

---

### `GET /api/history/<submeter>`

**Description**: Returns the **last 1 hour** of history for a given sub‑meter, aggregated into per‑minute averages.

- **Path parameter**:
  - `<submeter>` – a string such as `kitchen`, `hvac`, `laundry`, `electronics`.

- **Request body**: none.

- **Behavior**:
  - Filters records in `ENERGY_STORE` to those within the last hour.
  - Groups them by minute (using the first 16 characters of `timestamp` – `YYYY-MM-DDTHH:MM`).
  - For each minute, computes the average value of `sub_<submeter>`.

- **Response** (JSON array):

```json
[
  {
    "time": "2026-03-02T10:30",
    "value": 720.5
  },
  {
    "time": "2026-03-02T10:31",
    "value": 680.0
  }
]
```

Values are rounded to two decimal places.

---

### `GET /api/history_full`

**Description**: Returns the **last 5 records** from `ENERGY_STORE` without additional aggregation.

- **Request body**: none.

- **Response** (JSON array):

```json
[
  {
    "time": "2026-03-02T10:30:25.123456",
    "sub_kitchen": 350.0,
    "sub_hvac": 1200.0,
    "sub_laundry": 0.0,
    "sub_electronics": 400.0,
    "status": "HIGH_LOAD",
    "severity": "WARNING"
  },
  {
    "time": "...",
    "sub_kitchen": ...,
    "sub_hvac": ...,
    "sub_laundry": ...,
    "sub_electronics": ...,
    "status": "...",
    "severity": "..."
  }
]
```

Missing sub‑meter keys default to `0` in the response.

---

## 5. UI Routes

These routes render HTML pages using Jinja2 templates. They are primarily used by browsers and generally do not return JSON.

### `GET /`

- **Description**: Main dashboard page.
- **Template**: `dashboard.html`.

### `GET /devices`

- **Description**: Overview of device categories.
- **Template**: `devices.html`.

### `GET /device/<name>`

- **Description**: Device category detail view (e.g., `kitchen`, `hvac`).
- **Template**: `device_detail.html`.
- **Context**:
  - `name` – the category name from the URL.
  - `appliances` – list of appliances in that category.
  - `data` – latest record from `ENERGY_STORE` (or `{}` if empty).

### `GET /recommendations`

- **Description**: Page with energy‑saving recommendations and insights.
- **Template**: `energy_recommendations.html`.

### `GET /profile`

- **Description**: User profile / account page.
- **Template**: `profile.html`.

---

## 6. Summary

The Flask backend exposes:

- A compact set of **JSON APIs** for ML inference and data access.
- A set of **HTML routes** for user‑facing dashboards.

All endpoints are designed to be **simple, stateless, and easily consumable** by both browser clients and Node‑RED flows.

