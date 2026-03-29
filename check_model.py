import tensorflow as tf
import numpy as np
import joblib

MODEL_PATH = r"c:\mini-project\backend\model\energy_model.keras"
SCALER_PATH = r"c:\mini-project\backend\model\scaler.pkl"

print("=== LOADING MODEL ===")
model = tf.keras.models.load_model(MODEL_PATH)
model.summary()

scaler = joblib.load(SCALER_PATH)

print("\n=== SCALER INFO ===")
print(f"Mean (should be ~25, ~54, ~1013, ~74): {scaler.mean_}")
print(f"Std  (should be ~7, ~12, ~5, ~14):     {scaler.scale_}")

print("\n=== TEST PREDICTION (same as Colab) ===")
raw = np.array([[20.0, 50.0, 1007.0, 60.0]])
scaled = scaler.transform(raw)
print(f"Raw input:    {raw}")
print(f"Scaled input: {scaled}")

pred = model.predict(scaled, verbose=0)
print(f"\nPredicted Power: {pred[0][0]:.2f} MW")
print(f"Expected (Colab): ~458.25 MW")
