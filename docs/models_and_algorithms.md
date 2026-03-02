## Models and Algorithms

This document describes the **three main models** used in the project—**clustering (K‑Means)**, **LSTM forecasting**, and **Reinforcement Learning with Q‑Learning**—and how they interact.

---

## 1. Clustering – K‑Means

### 1.1 Objective

Partition historical energy usage into **three clusters** that correspond to:

- **NORMAL** usage,
- **HIGH_LOAD** usage,
- **OVERLOAD** usage.

This allows the system to quickly classify current conditions and support both visualization and control decisions.

### 1.2 Features

The clustering model uses IoT‑style features derived from the raw dataset:

- `power` – real power consumption in watts.
- `voltage` – supply voltage.
- `current` – current draw.
- `hour` – hour of the day (0–23).

The feature matrix is:

\[
X_{\text{cluster}} = [\text{power}, \text{voltage}, \text{current}, \text{hour}]
\]

### 1.3 Algorithm

- Algorithm: **K‑Means**, with `n_clusters = 3`.
- Implementation: `sklearn.cluster.KMeans`.
- Initialization: default K‑Means++ (via scikit‑learn).
- Random seed: `random_state=42` to ensure reproducibility.

Once trained, each data point is assigned to a cluster \(k \in \{0, 1, 2\}\).

To interpret these clusters, the sum of each centroid’s feature values is computed and used to order the clusters from **lowest** to **highest** total load. A mapping is then created:

- Lowest total load → `NORMAL`
- Middle total load → `HIGH_LOAD`
- Highest total load → `OVERLOAD`

At runtime, the backend:

1. Builds a feature vector from the current sub‑meter readings.
2. Applies `kmeans.predict`.
3. Maps the numeric cluster ID to the semantic label.

---

## 2. LSTM – Time Series Forecasting

### 2.1 Objective

Learn **temporal patterns of power consumption** and derive an **hourly baseline** that reflects typical usage throughout the day. This baseline can be used for:

- Detecting deviations and anomalies.
- Informing RL rewards or recommendations.
- Providing richer insight on the dashboard.

### 2.2 Data Preparation

1. Extract the `power` time series from the preprocessed DataFrame.
2. Normalize `power` to \([0, 1]\) using `MinMaxScaler`.
3. Construct supervised learning samples with a sliding window:

   - Window size: `window = 10`.
   - For each index \(i \geq \text{window}\), create:
     - Input: the previous 10 normalized values.
     - Target: the next value.

This yields training tensors:

\[
X_{\text{LSTM}} \in \mathbb{R}^{N \times 10 \times 1}, \quad y_{\text{LSTM}} \in \mathbb{R}^{N \times 1}
\]

### 2.3 Model Architecture

- Framework: TensorFlow / Keras.
- Model: `Sequential` with:
  - `LSTM(50, input_shape=(window, 1))`
  - `Dense(1)` output layer.
- Loss: Mean Squared Error (`"mse"`).
- Optimizer: Adam (`"adam"`).
- Training:
  - Epochs: `5` (capstone‑scale demo).
  - Batch size: `32`.

### 2.4 Baseline Computation

After training:

1. Use the trained model to predict on all sequences: `lstm_model.predict(X_lstm)`.
2. Inverse transform predictions to original units (watts) using the fitted scaler.
3. Align predictions with the original DataFrame (accounting for the sliding window offset).
4. Group predictions by hour and compute the **mean predicted power per hour**.

The result is a dictionary:

- `hourly_lstm_avg[hour] → average predicted power (W)` for each hour of the day.

This forms the **LSTM‑derived hourly baseline** stored in the hybrid model bundle.

---

## 3. Reinforcement Learning – Q‑Learning

### 3.1 Objective

Learn a **simple policy** that suggests actions under different load conditions, aiming to:

- Encourage **demand reduction** when the system is highly loaded.
- Provide a principled foundation for **recommendation logic**.

### 3.2 State and Action Space

- **States** (discretized by power level):
  - `0 = LOW`
  - `1 = MEDIUM`
  - `2 = HIGH`

  Derived from the current power \(P\) as:

  - \(P < 1000 \Rightarrow \text{LOW}\)
  - \(1000 \leq P < 2000 \Rightarrow \text{MEDIUM}\)
  - \(P \geq 2000 \Rightarrow \text{HIGH}\)

- **Actions**:
  - `NORMAL` – keep usage as is.
  - `SHIFT` – shift usage to another time.
  - `REDUCE` – actively reduce demand now.

The Q‑table has shape:

\[
Q \in \mathbb{R}^{3 \times 3} \quad (\text{states} \times \text{actions})
\]

### 3.3 Reward Function

The reward is shaped to favor reduction under high load:

- If state is `HIGH` and action is `REDUCE` → **+10**.
- If state is `HIGH` and action is `NORMAL` → **−10**.
- All other combinations → small positive reward (e.g. **+2**).

This encourages the agent to:

- Learn that **REDUCE** is the best response when in HIGH state.
- Avoid staying **NORMAL** under overload conditions.

### 3.4 Q‑Learning Updates

For each training iteration:

1. Sample a random power value from the dataset.
2. Map power to a state index via `get_state(power)`.
3. Sample a random action index.
4. Compute reward from `(state, action)`.
5. Update Q‑value:

\[
Q(s, a) \leftarrow Q(s, a) + \alpha \left( r + \gamma \max_{a'} Q(s, a') - Q(s, a) \right)
\]

with:

- Learning rate \(\alpha = 0.1\),
- Discount factor \(\gamma = 0.9\),
- Number of iterations: e.g. `1000`.

The resulting `Q` matrix and `actions` list are stored in the hybrid model bundle.

### 3.5 Policy Extraction

The **greedy policy** at deployment time is:

\[
\pi(s) = \arg\max_a Q(s, a)
\]

Combined with the clustering and hourly baseline, this provides a **multi‑layer decision framework**:

- Clustering → identify current regime (NORMAL / HIGH_LOAD / OVERLOAD).
- LSTM baseline → compare actual load to expected patterns.
- Q‑Learning policy → propose recommended actions (NORMAL, SHIFT, REDUCE).

---

## 4. Hybrid Model Bundle

The `full_hybrid_energy_model.pkl` file contains:

- `kmeans` – trained scikit‑learn K‑Means instance.
- `lstm_model` – trained Keras model.
- `scaler` – `MinMaxScaler` fitted on power.
- `Q_table` – NumPy array with learned Q‑values.
- `actions` – list of action labels (`["NORMAL", "SHIFT", "REDUCE"]`).
- `hourly_lstm_avg` – dict mapping hour → baseline power.

This bundle is loaded at runtime in `app.py` and used across the system to:

- Classify the current measurement,
- Reason about expected vs. actual load,
- Provide recommendations based on the learned RL policy.

---

## 5. Summary

The capstone’s intelligence layer is **hybrid by design**:

- **Unsupervised learning** (K‑Means) captures natural usage regimes.
- **Deep learning** (LSTM) captures temporal dynamics and baselines.
- **Reinforcement learning** (Q‑Learning) encodes prescriptive actions.

Together, they form a cohesive framework for the **Smart Energy Monitoring System (SEMS)** and smart, data‑driven energy management.

