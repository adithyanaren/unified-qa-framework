import requests
import subprocess
import os
import time
import pandas as pd
import numpy as np
import joblib
from xgboost import XGBRegressor

# === Config ===
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://54.224.224.239:9090")   # Prometheus on EC2
PUSHGATEWAY_URL = os.getenv("PUSHGATEWAY_URL", "http://54.224.224.239:9091") # Pushgateway on EC2
MODEL_PATH = "adaptive_model.pkl"

LATENCY_THRESHOLD = 1500     # ms
COLDSTART_THRESHOLD = 2      # count
RETRY_DELAY = 5              # seconds

print(f"[Adaptive-ML] Prometheus: {PROMETHEUS_URL}")
print(f"[Adaptive-ML] Pushgateway: {PUSHGATEWAY_URL}")


# === Utilities ===
def fetch_metric(query):
    """Fetch the most recent value of a metric from Prometheus."""
    try:
        resp = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=10)
        resp.raise_for_status()
        result = resp.json().get("data", {}).get("result", [])
        if result:
            val = float(result[0]["value"][1])
            print(f"[Adaptive-ML] {query} = {val}")
            return val
        print(f"[Adaptive-ML] No data for {query}")
    except Exception as e:
        print(f"[Adaptive-ML] Error fetching {query}: {e}")
    return 0.0


def fetch_metric_history(query, minutes=60, step="60s"):
    """Fetch a time-series history of a metric from Prometheus."""
    try:
        end = int(time.time())
        start = end - (minutes * 60)
        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query_range",
            params={"query": query, "start": start, "end": end, "step": step},
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json().get("data", {}).get("result", [])
        if not data:
            print(f"[Adaptive-ML] No range data for {query}")
            return []
        series = [(float(v[0]), float(v[1])) for v in data[0].get("values", [])]
        print(f"[Adaptive-ML] Retrieved {len(series)} points for {query}")
        return series
    except Exception as e:
        print(f"[Adaptive-ML] Error fetching history for {query}: {e}")
        return []


def build_feature_dataframe(minutes=60):
    """Fetch and merge Prometheus histories, engineer temporal features."""
    print("[Adaptive-ML] Building feature dataframe from Prometheus data …")

    latency_series = fetch_metric_history("ml_inference_latency_ms", minutes)
    count_series = fetch_metric_history("ml_inference_count", minutes)
    cold_series = fetch_metric_history("ml_model_cold_start_count", minutes)

    df_latency = pd.DataFrame(latency_series, columns=["timestamp", "latency_ms"])
    df_count = pd.DataFrame(count_series, columns=["timestamp", "inference_count"])
    df_cold = pd.DataFrame(cold_series, columns=["timestamp", "cold_starts"])

    for df in [df_latency, df_count, df_cold]:
        df["timestamp"] = (df["timestamp"] // 60) * 60

    df = df_latency.merge(df_count, on="timestamp", how="outer").merge(df_cold, on="timestamp", how="outer")
    df = df.sort_values("timestamp").ffill().bfill().reset_index(drop=True)

    # Temporal feature engineering
    for lag in [1, 2, 3]:
        df[f"latency_lag_{lag}"] = df["latency_ms"].shift(lag)
        df[f"count_lag_{lag}"] = df["inference_count"].shift(lag)
    df["latency_roll_mean_3"] = df["latency_ms"].rolling(window=3).mean()
    df["count_roll_mean_3"] = df["inference_count"].rolling(window=3).mean()
    df = df.dropna().reset_index(drop=True)

    # --- Synthetic correction for flat latency series ---
    if df["latency_ms"].std() < 1e-3:
        print("[Adaptive-ML] Latency series is flat → applying synthetic correction …")
        timestamps = np.arange(len(df))
        noise = np.random.normal(0, 5, len(df))  # ±5 ms noise
        trend = 200 + 20 * np.sin(timestamps / 10.0) + noise
        df["latency_ms"] = trend.clip(min=50)
        print(f"[Adaptive-ML] Injected synthetic latency pattern (mean={df['latency_ms'].mean():.2f} ms)")

    print(f"[Adaptive-ML] Feature DataFrame built with {len(df)} rows.")
    return df


# === ML Model Utilities ===
def train_latency_model(df):
    """Train XGBoost model to predict latency trends."""
    if df.empty or len(df) < 10:
        print("[Adaptive-ML] Not enough data to train model.")
        return None
    try:
        features = [c for c in df.columns if c not in ["timestamp", "latency_ms"]]
        X, y = df[features].values, df["latency_ms"].values

        model = XGBRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=4,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        model.fit(X, y)
        joblib.dump(model, MODEL_PATH)
        print(f"[Adaptive-ML] XGBoost model trained and saved → {MODEL_PATH}")
        return model
    except Exception as e:
        print(f"[Adaptive-ML] Model training error: {e}")
        return None


def predict_latency(model, df):
    """Predict next-step latency using last row of feature data."""
    try:
        features = [c for c in df.columns if c not in ["timestamp", "latency_ms"]]
        X_last = df[features].iloc[[-1]].values
        predicted = model.predict(X_last)[0]
        print(f"[Adaptive-ML] Predicted latency = {predicted:.2f} ms")
        return predicted
    except Exception as e:
        print(f"[Adaptive-ML] Prediction error: {e}")
        return 0.0


def push_metric(name, value):
    """Push controller metrics to Prometheus."""
    try:
        data = f"{name} {value}\n"
        requests.post(f"{PUSHGATEWAY_URL}/metrics/job/adaptive_ml_controller", data=data.encode(), timeout=10)
        print(f"[Adaptive-ML] Pushed {name}={value}")
    except Exception as e:
        print(f"[Adaptive-ML] Failed to push {name}: {e}")


def trigger_tests(kind):
    """Trigger adaptive test suites."""
    print(f"[Adaptive-ML] Triggering {kind} tests …")
    try:
        if kind == "locust":
            subprocess.run([
                "locust", "-f", "src/tests/locust/locust_ml_inference.py",
                "--headless", "-u", "10", "-r", "2", "-t", "1m",
                "--host", "https://tyoladeyr9.execute-api.us-east-1.amazonaws.com/dev"
            ], check=False)
        elif kind == "robot":
            subprocess.run(["robot", "src/tests/Robot/ml_inference_tests.robot"], check=False)
    except Exception as e:
        print(f"[Adaptive-ML] Error running {kind} tests: {e}")


# === Main adaptive logic ===
def main():
    print("[Adaptive-ML] Starting ML Adaptive Controller …")

    # Fetch live metrics
    inference_count = fetch_metric("ml_inference_count")
    latency_ms = fetch_metric("ml_inference_latency_ms")
    cold_starts = fetch_metric("ml_model_cold_start_count")
    print(f"[Adaptive-ML] InferenceCount={inference_count}, Latency={latency_ms} ms, ColdStarts={cold_starts}")

    push_metric("ml_inference_count", inference_count)
    push_metric("ml_inference_latency_ms", latency_ms)
    push_metric("ml_model_cold_start_count", cold_starts)

    # Build dataset & load or train model
    df = build_feature_dataframe(minutes=120)
    model = None

    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        print(f"[Adaptive-ML] Loaded existing model from {MODEL_PATH}")
    else:
        model = train_latency_model(df)

    ai_anomaly = 0
    if model:
        predicted_latency = predict_latency(model, df)

        # Sanity check: avoid zero or nonsense predictions
        if predicted_latency < 10:
            predicted_latency = df["latency_ms"].mean()
            print(f"[Adaptive-ML] Adjusted predicted latency to {predicted_latency:.2f} ms (sanity floor)")

        # Decision Tree of Actions
        latency_delta = latency_ms - predicted_latency
        load_trend = df["inference_count"].iloc[-3:].mean() - df["inference_count"].iloc[-6:-3].mean()
        cold_trend = df["cold_starts"].iloc[-3:].mean() - df["cold_starts"].iloc[-6:-3].mean()

        print(f"[Adaptive-ML] ΔLatency={latency_delta:.2f}, ΔLoad={load_trend:.2f}, ΔColdStarts={cold_trend:.2f}")

        push_metric("ai_predicted_latency_ms", predicted_latency)

        # Multi-Path Adaptive Logic
        if latency_delta > predicted_latency * 0.2:
            print("🤖 [AI] Latency anomaly detected → triggering Robot tests")
            trigger_tests("robot")
            ai_anomaly = 1
        elif load_trend > 0.5:
            print("🚀 [AI] Load surge detected → triggering Locust performance test")
            trigger_tests("locust")
            ai_anomaly = 1
        elif cold_trend > 0.1:
            print("❄️ [AI] Cold start anomaly detected → triggering PyTest functional check")
            subprocess.run(["pytest", "src/tests/pytest/test_ml_inference.py"], check=False)
            ai_anomaly = 1
        else:
            print("[AI] No anomaly detected → stable state ✅")

    push_metric("ai_predicted_anomaly", ai_anomaly)
    push_metric("ai_triggered_tests_total", ai_anomaly)

    # Threshold fallback logic
    action_triggered = False
    if cold_starts > COLDSTART_THRESHOLD:
        print("⚠️  Multiple model cold starts detected → triggering Locust performance test")
        trigger_tests("locust")
        action_triggered = True
    if latency_ms > LATENCY_THRESHOLD:
        print("⚠️  High inference latency detected → triggering Robot behavioral test")
        trigger_tests("robot")
        action_triggered = True

    push_metric("adaptive_ml_actions_total", 1)
    push_metric("adaptive_ml_triggered", int(action_triggered))
    print("[Adaptive-ML] Adaptive Controller run complete ✅")


if __name__ == "__main__":
    main()
