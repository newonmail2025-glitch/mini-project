import requests
import json

API_BASE = "http://localhost:8000"

scenarios = {
    "❄️ Cold Winter": {"AT": 5.0,  "V": 40.0, "AP": 1015.0, "RH": 60.0},
    "☀️ Hot Summer":  {"AT": 35.0, "V": 70.0, "AP": 1005.0, "RH": 50.0},
}

for name, params in scenarios.items():
    print(f"\nTesting {name}...")
    try:
        res = requests.post(f"{API_BASE}/predict", json=params, timeout=5)
        if res.status_code == 200:
            print(f"✅ Result: {json.dumps(res.json(), indent=2)}")
        else:
            print(f"❌ Error {res.status_code}: {res.text}")
    except Exception as e:
        print(f"❌ Failed to reach backend: {e}")
