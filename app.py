import warnings
warnings.filterwarnings(
    "ignore",
    message="X does not have valid feature names"
)

import os
import pickle
import numpy as np
from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta

# =====================================================
# LOAD TRAINED ML MODELS
# =====================================================
MODEL_PATH = os.path.join("models", "full_hybrid_energy_model.pkl")
with open(MODEL_PATH, "rb") as f:
    bundle = pickle.load(f)

kmeans = bundle["kmeans"]
lstm_model = bundle.get("lstm_model")  # optional

# -----------------------------------------------------
# Determine cluster meaning (low → high)
# -----------------------------------------------------
centers = kmeans.cluster_centers_
center_loads = centers.sum(axis=1)
order = np.argsort(center_loads)

CLUSTER_LABELS = {
    int(order[0]): "NORMAL",
    int(order[1]): "HIGH_LOAD",
    int(order[2]): "OVERLOAD"
}

# print("\n================ CENTROIDS ================")
# for i, c in enumerate(centers):
#     print(f"Cluster {i}: {c} | sum = {c.sum():.2f}")

# print("\nCluster roles:")
# print("NORMAL   →", order[0])
# print("HIGH     →", order[1])
# print("OVERLOAD →", order[2])
# print("==========================================\n")

# =====================================================
# FLASK APP
# =====================================================
app = Flask(__name__)
print("\n================ API STARTED ================\n")

# =====================================================
# IN-MEMORY DATA STORE 
# =====================================================
ENERGY_STORE = []   # list of dicts (acts like DB)

APPLIANCE_MAP = {
    "kitchen": ["Microwave", "Induction", "Mixer"],
    "hvac": ["AC", "Fan"],
    "laundry": ["Washing Machine"],
    "electronics": ["TV", "Laptop", "Router"]
}

# =====================================================
# 🔹 ML CLASSIFICATION ENDPOINT
# =====================================================
@app.route("/predict", methods=["POST"])
def predict():
    print("\n>>> /predict called")

    data = request.get_json(force=True, silent=True)
    print("Incoming JSON:", data)

    if not data or "features" not in data:
        return jsonify({"error": "features missing"}), 400

    try:
        # features = [hour, kitchen, hvac, laundry, electronics, voltage, current]
        sub_kitchen = float(data["features"][1])
        sub_hvac = float(data["features"][2])
        sub_laundry = float(data["features"][3])
        sub_electronics = float(data["features"][4])
    except Exception as e:
        print("Feature parsing error:", e)
        return jsonify({"error": "invalid feature format"}), 400

    X = np.array([[sub_kitchen, sub_hvac, sub_laundry, sub_electronics]])
    cluster_id = int(kmeans.predict(X)[0])
    prediction = CLUSTER_LABELS.get(cluster_id, "UNKNOWN")

    print("Prediction:", prediction, "Cluster:", cluster_id)

    return jsonify({
        "prediction": prediction,
        "cluster_id": cluster_id,
        "used_features": [
            "sub_kitchen",
            "sub_hvac",
            "sub_laundry",
            "sub_electronics"
        ]
    })


# =====================================================
# LSTM DAILY FORECAST
# =====================================================
# @app.route("/forecast/day", methods=["GET"])
# def day_forecast():
#     print(">>> /forecast/day called")

#     if lstm_model is None:
#         return jsonify({
#             "hourly_total_load": [
#                 600, 550, 520, 500, 520, 650,
#                 900, 1200, 1300, 1100,
#                 1000, 1050, 1500, 1600,
#                 1700, 1600, 1900,
#                 2100, 4000, 3500, 3200,
#                 2800, 1800, 900
#             ],
#             "source": "fallback"
#         })

#     seed = np.array([
#         600, 550, 520, 500, 520, 650,
#         900, 1200, 1300, 1100,
#         1000, 1050, 1500, 1600,
#         1700, 1600, 1900,
#         2100, 4000, 3500, 3200,
#         2800, 1800, 900
#     ]).reshape(1, 24, 1)

#     preds = lstm_model.predict(seed, verbose=0).flatten()
#     preds = np.clip(preds, 400, 4500)

#     return jsonify({
#         "hourly_total_load": [round(float(v), 2) for v in preds],
#         "source": "lstm"
#     })


# =====================================================
# RECEIVE DATA FROM NODE-RED / ML
# =====================================================
@app.route("/node-red-input", methods=["POST"])
def store():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "No JSON received"}), 400

    # # 🔥 REQUIRED FIX: default submeter values
    # data.setdefault("sub_kitchen", 0)
    # data.setdefault("sub_hvac", 0)
    # data.setdefault("sub_laundry", 0)
    # data.setdefault("sub_electronics", 0)

    data["timestamp"] = datetime.now().isoformat()
    ENERGY_STORE.append(data)

    if len(ENERGY_STORE) > 200:
        ENERGY_STORE.pop(0)

    return jsonify({"status": "SUCCESS"}), 200


# =====================================================
# API – LATEST DATA
# =====================================================
@app.route("/api/latest")
def latest():
    if not ENERGY_STORE:
        return jsonify({})
    return jsonify(ENERGY_STORE[-1])


# =====================================================
# API – LAST 1 HOUR HISTORY
# =====================================================
@app.route("/api/history/<submeter>")
def history(submeter):
    one_hour_ago = datetime.now() - timedelta(hours=1)
    buckets = {}

    for r in ENERGY_STORE:
        ts = datetime.fromisoformat(r["timestamp"])
        if ts < one_hour_ago:
            continue

        minute_key = r["timestamp"][:16]
        value = r.get(f"sub_{submeter}", 0)
        buckets.setdefault(minute_key, []).append(value)

    return jsonify([
        {"time": k, "value": round(sum(v)/len(v), 2)}
        for k, v in buckets.items()
    ])


# =====================================================
# API – LAST 5 RECORDS
# =====================================================
@app.route("/api/history_full")
def history_full():
    return jsonify([
        {
            "time": r.get("timestamp"),
            "sub_kitchen": r.get("sub_kitchen", 0),
            "sub_hvac": r.get("sub_hvac", 0),
            "sub_laundry": r.get("sub_laundry", 0),
            "sub_electronics": r.get("sub_electronics", 0),
            "status": r.get("status"),
            "severity": r.get("severity")
        }
        for r in ENERGY_STORE[-5:]
    ])


# =====================================================
# UI ROUTES
# =====================================================
@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/devices")
def devices():
    return render_template("devices.html")

@app.route("/device/<name>")
def device_detail(name):
    latest = ENERGY_STORE[-1] if ENERGY_STORE else {}
    return render_template(
        "device_detail.html",
        name=name,
        appliances=APPLIANCE_MAP.get(name, []),
        data=latest
    )

@app.route("/recommendations")
def recommendations():
    return render_template("energy_recommendations.html")

@app.route("/profile")
def profile():
    return render_template("profile.html")


# =====================================================
# HEALTH CHECK
# =====================================================
@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# =====================================================
# RUN APP
# =====================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
