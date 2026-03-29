from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import tensorflow as tf
import numpy as np
import os
import joblib
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from pydantic import BaseModel
from utils.weather import fetch_weather_data, estimate_vacuum_value
from utils.preprocessor import preprocess_input

load_dotenv()

# ─── Data Models ────────────────────────────────────────────────────────────────
class PredictionInput(BaseModel):
    AT: float
    V: float
    AP: float
    RH: float

# ─── Constants (Absolute Paths) ──────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.normpath(os.path.join(BASE_DIR, "model", "energy_model.keras"))
SCALER_PATH = os.path.normpath(os.path.join(BASE_DIR, "model", "scaler.pkl"))
RATED_CAPACITY = 480.0

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n" + "="*50)
    print("📡 BACKEND SERVER STARTUP")
    print("="*50)
    
    # Load Model
    if os.path.exists(MODEL_PATH):
        try:
            app.state.model = tf.keras.models.load_model(MODEL_PATH)
            print(f"✅ OK: Model loaded from {MODEL_PATH}")
        except Exception as e:
            print(f"❌ ERROR: Model load failed: {e}")
            app.state.model = None
    else:
        print(f"❌ FAIL: Model file not found at {MODEL_PATH}")
        app.state.model = None

    # Load Scaler
    if os.path.exists(SCALER_PATH):
        try:
            # Explicitly load with joblib
            app.state.scaler = joblib.load(SCALER_PATH)
            print(f"✅ OK: Scaler loaded from {SCALER_PATH}")
            
            # --- STARTUP TEST ---
            test_raw = np.array([[20.0, 50.0, 1007.0, 60.0]])
            test_scaled = app.state.scaler.transform(test_raw)
            print(f"🧪 STARTUP TEST: Original values: {test_raw}")
            print(f"🧪 STARTUP TEST: Scaled values: {test_scaled}")
            
            # Check if scaled values are still big (Raw)
            if np.allclose(test_raw, test_scaled):
                print("⚠️  WARNING: Scaler is doing NOTHING! It's an identity transform.")
            else:
                print("✨ SUCCESS: Scaler is transforming the data correctly.")
            # --------------------
            
        except Exception as e:
            print(f"❌ ERROR: Scaler load or test failed: {e}")
            app.state.scaler = None
    else:
        print(f"⚠️  WARNING: Scaler file not found at {SCALER_PATH}")
        app.state.scaler = None
        
    yield
    # Cleanup (only if you want to force reload on change)
    # app.state.model = None
    # app.state.scaler = None

# ─── App Initialization ─────────────────────────────────────────────────────────
app = FastAPI(
    title="Power Plant Energy Prediction API",
    version="1.3.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Helpers ────────────────────────────────────────────────────────────────────
def run_prediction(at: float, v: float, ap: float, rh: float) -> dict:
    """Run ANN prediction and return structured result."""
    if not hasattr(app.state, "model") or app.state.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded on server.")

    # 1. Prepare raw input
    raw_input = preprocess_input(at, v, ap, rh) # [[at, v, ap, rh]]
    
    # 2. Scale it
    if hasattr(app.state, "scaler") and app.state.scaler is not None:
        try:
            final_input = app.state.scaler.transform(raw_input)
            print(f"📡 PREDICT: Raw[{at}, {v}, {ap}, {rh}] -> Scaled{final_input[0]}")
        except Exception as e:
            print(f"⚠️ Prediction Scaling failed: {e}")
            final_input = raw_input
    else:
        final_input = raw_input
        print(f"⚠️ PREDICT: Running WITHOUT scaling (Expect wrong results!)")

    # 3. AI Inference
    prediction = app.state.model.predict(final_input, verbose=0)
    pow_out = float(prediction[0][0])
    
    print(f"⚡ PREDICT RESULT: {pow_out:.2f} MW")
    
    return {
        "predicted_power": round(pow_out, 2),
        "rated_capacity": RATED_CAPACITY,
        "deviation": round(RATED_CAPACITY - pow_out, 2),
    }

# ─── Endpoints ──────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "online",
        "model_loaded": hasattr(app.state, "model") and app.state.model is not None,
        "scaler_loaded": hasattr(app.state, "scaler") and app.state.scaler is not None,
        "version": "1.3.0"
    }

@app.post("/predict", tags=["Prediction"])
async def predict(data: PredictionInput):
    return run_prediction(data.AT, data.V, data.AP, data.RH)

@app.get("/weather-prediction", tags=["Weather Prediction"])
async def weather_prediction(city: str = Query(..., description="City name for live weather")):
    weather = await fetch_weather_data(city)
    if not weather:
        raise HTTPException(status_code=404, detail="City not found.")
    
    at = weather["temp"]
    ap = weather["pressure"]
    rh = weather["humidity"]
    v = estimate_vacuum_value(at)
    
    result = run_prediction(at, v, ap, rh)
    return {**result, "city": weather["city"], "temperature": at, "pressure": ap, "humidity": rh, "v": v}
# Trigger reload
