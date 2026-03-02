# =========================
# ALL IMPORTS (FULL)
# =========================
# import os
# os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"   # silence TF logs

import os
import numpy as np
import pandas as pd
import pickle

from sklearn.cluster import KMeans
from sklearn.preprocessing import MinMaxScaler

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

# # 🔒 Prevent macOS thread lock spam
# tf.config.threading.set_intra_op_parallelism_threads(1)
# tf.config.threading.set_inter_op_parallelism_threads(1)


# =========================
# LOAD & PREPROCESS DATA
# =========================
df = pd.read_csv(
    "household_power_consumption.txt",
    sep=";",
    na_values="?",
    low_memory=False
)

# Combine Date + Time → timestamp
df["timestamp"] = pd.to_datetime(
    df["Date"] + " " + df["Time"],
    format="%d/%m/%Y %H:%M:%S"
)

# Convert numeric columns
num_cols = [
    "Global_active_power",
    "Global_reactive_power",
    "Voltage",
    "Global_intensity",
    "Sub_metering_1",
    "Sub_metering_2",
    "Sub_metering_3"
]

df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")
df.dropna(inplace=True)

# =========================
# FEATURE ENGINEERING (IoT STYLE)
# =========================
df["power"] = df["Global_active_power"] * 1000  # kW → W
df["voltage"] = df["Voltage"]
df["current"] = df["Global_intensity"]
df["temperature"] = 25  # assumed ambient
df["hour"] = df["timestamp"].dt.hour

# =========================
# 1️⃣ CLUSTERING (KMeans)
# =========================
cluster_features = df[["power", "voltage", "current", "hour"]]

kmeans = KMeans(n_clusters=3, random_state=42)
df["usage_cluster"] = kmeans.fit_predict(cluster_features)

# =========================
# 2️⃣ LSTM (POWER FORECAST)
# =========================
scaler = MinMaxScaler()
scaled_power = scaler.fit_transform(df[["power"]])

X_lstm, y_lstm = [], []
window = 10

for i in range(window, len(scaled_power)):
    X_lstm.append(scaled_power[i - window:i])
    y_lstm.append(scaled_power[i])

X_lstm = np.array(X_lstm)
y_lstm = np.array(y_lstm)

lstm_model = Sequential([
    LSTM(50, input_shape=(window, 1)),
    Dense(1)
])

lstm_model.compile(optimizer="adam", loss="mse")
lstm_model.fit(X_lstm, y_lstm, epochs=5, batch_size=32, verbose=1)

# =========================
# LSTM → HOURLY AVERAGE BASELINE (OFFLINE)
# =========================
lstm_predictions = lstm_model.predict(X_lstm, verbose=0)

# Inverse scale → watts
lstm_predictions_watts = scaler.inverse_transform(lstm_predictions)

# Align predictions with dataframe hours
df_lstm = df.iloc[window:].copy()
df_lstm["lstm_predicted_power"] = lstm_predictions_watts.flatten()

# Compute hourly averages
hourly_lstm_avg = (
    df_lstm
    .groupby("hour")["lstm_predicted_power"]
    .mean()
    .round(0)
    .astype(int)
)

print("\nLSTM-DERIVED HOURLY AVERAGE LOAD (WATTS)")
print("========================================")
for hour, value in hourly_lstm_avg.items():
    print(f"Hour {hour:02d}: {value} W")

# =========================
# REINFORCEMENT LEARNING (Q-Learning)
# =========================
states = ["LOW", "MEDIUM", "HIGH"]
actions = ["NORMAL", "SHIFT", "REDUCE"]

Q = np.zeros((len(states), len(actions)))

def get_state(power):
    if power < 1000:
        return 0
    elif power < 2000:
        return 1
    else:
        return 2

def reward(state, action):
    if state == 2 and action == 2:   # HIGH + REDUCE
        return 10
    if state == 2 and action == 0:   # HIGH + NORMAL
        return -10
    return 2

alpha, gamma = 0.1, 0.9

for _ in range(1000):
    p = np.random.choice(df["power"])
    s = get_state(p)
    a = np.random.randint(len(actions))
    r = reward(s, a)
    Q[s, a] = Q[s, a] + alpha * (r + gamma * np.max(Q[s]) - Q[s, a])

# =========================
# RULE ENGINE (SAFETY)
# =========================
def rule_engine(predicted_power):
    if predicted_power > 2500:
        return "FORCE REDUCE"
    return None

# =========================
# SAVE FULL HYBRID MODEL
# =========================
hybrid_model = {
    "kmeans": kmeans,
    "lstm_model": lstm_model,
    "scaler": scaler,
    "Q_table": Q,
    "actions": actions,
    "hourly_lstm_avg": hourly_lstm_avg.to_dict()
}

os.makedirs("models", exist_ok=True)

with open(os.path.join("models", "full_hybrid_energy_model.pkl"), "wb") as f:
    pickle.dump(hybrid_model, f)

print("\nFULL HYBRID MODEL TRAINED & SAVED")
print("   (Clustering + LSTM + RL + Hourly Baseline)")
