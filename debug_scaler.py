import joblib
import os
import numpy as np

SCALER_PATH = r"c:\mini-project\backend\model\scaler.pkl"

if os.path.exists(SCALER_PATH):
    scaler = joblib.load(SCALER_PATH)
    print(f"Type: {type(scaler)}")
    if hasattr(scaler, 'mean_'):
        print(f"Mean: {scaler.mean_}")
    if hasattr(scaler, 'scale_'):
        print(f"Scale/Std: {scaler.scale_}")
    
    test_val = np.array([[20.0, 50.0, 1013.0, 60.0]])
    scaled = scaler.transform(test_val)
    print(f"Raw Input: {test_val}")
    print(f"Scaled Input: {scaled}")
else:
    print("Scaler not found!")
