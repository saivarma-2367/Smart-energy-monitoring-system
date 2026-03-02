import numpy as np
import pandas as pd
import pickle

# =====================================================
# LOAD HYBRID MODEL
# =====================================================
with open("full_hybrid_energy_model.pkl", "rb") as f:
    model = pickle.load(f)

kmeans = model["kmeans"]
lstm = model["lstm_model"]
scaler = model["scaler"]
Q = model["Q_table"]
actions = model["actions"]

# =====================================================
# LOAD IoT DATA
# =====================================================
df = pd.read_csv("energy_data.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["hour"] = df["timestamp"].dt.hour
df["power"] = df["power"].astype(float)

# Features MUST match training exactly
cluster_features = df[["power", "voltage", "current", "hour"]]

df["usage_cluster"] = kmeans.predict(cluster_features)


# =====================================================
# LSTM FORECAST
# =====================================================
scaled = scaler.transform(df[["power"]])
last_seq = scaled[-10:].reshape(1, 10, 1)

predicted_power = scaler.inverse_transform(
    lstm.predict(last_seq, verbose=0)
)[0][0]

# =====================================================
# RL DECISION
# =====================================================
def get_state(power):
    if power < 1000:
        return 0
    elif power < 2000:
        return 1
    else:
        return 2

state = get_state(predicted_power)
action_index = np.argmax(Q[state])
rl_action = actions[action_index]

def rule_engine(predicted_power):
    if predicted_power > 2500:
        return "FORCE REDUCE"
    return None

# =====================================================
# RULE OVERRIDE
# =====================================================
rule_action = rule_engine(predicted_power)
final_action = rule_action if rule_action else rl_action

# =====================================================
# OUTPUT
# =====================================================
print("\n🔌 HYBRID ENERGY DECISION OUTPUT\n")
print(f"Usage Cluster        : {df['usage_cluster'].iloc[-1]}")
print(f"Predicted Power (W)  : {predicted_power:.2f}")
print(f"RL Suggested Action  : {rl_action}")
print(f"Final Action         : {final_action}")


