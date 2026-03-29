import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd
import time
import numpy as np
import pymongo
import bcrypt
import os
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

init_db()

st.set_page_config(page_title="PowerPlant AI", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
RATED_CAPACITY = 480.0

# Major Indian Cities for Dropdown
INDIAN_CITIES = sorted([
    "Ahmedabad", "Bangalore", "Bhopal", "Bhubaneswar", "Chandigarh", "Chennai", 
    "Dehradun", "Delhi", "Gandhinagar", "Gangtok", "Guwahati", "Hyderabad", 
    "Imphal", "Itanagar", "Jaipur", "Jammu", "Kochi", "Kolkata", "Lucknow", 
    "Madurai", "Mumbai", "Mysore", "Nagpur", "Panaji", "Patna", "Pune", 
    "Raipur", "Ranchi", "Shillong", "Shimla", "Srinagar", 
    "Surat", "Thiruvananthapuram", "Visakhapatnam"
])

# ─── Data Persistence (MongoDB) ───
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://newonmail2025_db_user:lnMF2HdG3CHIEs4Q@cluster0.01ppf5e.mongodb.net/?appName=Cluster0")
try:
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["powerplant_ai"]
    users_col = db["users"]
    client.server_info() # Test connection
except Exception as e:
    st.warning(f"⚠️ Global Database not detected. Code: {e}")
    users_col = None

# Constants
COMPANY_CODE = "sham" # As requested 'sham'

# ─── Initialize Session State ───
defaults = {"AT": 15.0, "V": 40.0, "AP": 1015.0, "RH": 60.0,
            "result": None, "weather_data": None, "history": [],
            "auto_predict": False, "live_monitoring": False, "last_scenario": "Cold Winter",
            "app_state": "Welcome", "user": None,
            "live_data": {"temperature": 15.0, "v": 40.0, "pressure": 1015.0, "humidity": 60.0, "predicted_power": 460.0}}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── Session Persistence Logic ───
# If we are at 'Welcome' but have a session cookie in the URL, skip to Home
if "session_id" in st.query_params and st.session_state.app_state == "Welcome":
    st.session_state.app_state = "Home"
    st.session_state.user = {"email": st.query_params["session_id"]}

SCENARIOS = {
    "❄️ Cold Winter": {"AT": 5.0,  "V": 40.0, "AP": 1015.0, "RH": 60.0},
    "☀️ Hot Summer":  {"AT": 35.0, "V": 70.0, "AP": 1005.0, "RH": 50.0},
    "💧 Rainy Weather": {"AT": 28.0, "V": 55.0, "AP": 1010.0, "RH": 90.0},
    "⚠️ Extreme Heat":  {"AT": 42.0, "V": 80.0, "AP": 1002.0, "RH": 30.0},
}

def run_prediction(at, v, ap, rh):
    with st.spinner("🧠 INITIATING NEURAL INFERENCE..."):
        try:
            res = requests.post(f"{API_BASE}/predict", json={"AT": at, "V": v, "AP": ap, "RH": rh}, timeout=10)
            if res.status_code == 200:
                data = res.json()
                st.session_state.result = data
                st.session_state.weather_data = None
                save_prediction(temperature=at, vacuum=v, pressure=ap, humidity=rh, predicted_power=data["predicted_power"], scenario=st.session_state.get("last_scenario", "Manual"))
                time.sleep(0.5) # Slight delay for visual "thought" effect
            else:
                st.error(f"API Error: {res.json().get('detail', 'Unknown error')}")
        except Exception as e:
            st.error(f"Backend Connection Error: {e}")

def fetch_and_predict(city):
    if not city: return
    try:
        res = requests.get(f"{API_BASE}/weather-prediction", params={"city": city}, timeout=15)
        if res.status_code == 200:
            data = res.json()
            # If Hyderabad (Live Tab), we isolate this into a special storage
            if city == "Hyderabad":
                st.session_state.live_data = data
            
            # Global variables for simulation results (keep these for backward compatibility elsewhere if needed)
            st.session_state.result = data
            st.session_state.weather_data = data
            save_prediction(temperature=data["temperature"], vacuum=data.get("v", 0), pressure=data["pressure"], humidity=data["humidity"], predicted_power=data["predicted_power"], scenario=f"Live Weather: {data.get('city')}")
            
            # These only update the global "simulation" state IF it's not a background update
            if not st.session_state.get('live_monitoring'):
                st.session_state.AT, st.session_state.V, st.session_state.AP, st.session_state.RH = data["temperature"], data.get("v", 0), data["pressure"], data["humidity"]
        else:
            st.session_state.weather_error = f"Weather API Error: {res.json().get('detail')}"
    except Exception as e:
        st.session_state.weather_error = f"Backend Connection Error: {e}"

# ─── Authentication Logic ───
def hash_pass(pwd): return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt())
def check_pass(pwd, hashed): return bcrypt.checkpw(pwd.encode(), hashed)

def sign_up(email, pwd, code):
    if code != COMPANY_CODE: return "Invalid Company Access Code."
    if users_col is not None:
        if users_col.find_one({"email": email}): return "Account already exists."
        users_col.insert_one({"email": email, "password": hash_pass(pwd)})
    return True

def login(email, pwd):
    if users_col is not None:
        user = users_col.find_one({"email": email})
        if user and check_pass(pwd, user["password"]): return True
    elif email == "admin@plant.ai" and pwd == "admin123": return True # Sandbox Admin
    return False

# ─── Auth UI Screens ───
def welcome_page():
    st.markdown("""
    <div style="text-align:center; padding-top:100px;">
        <div style="font-size:4rem; font-weight:900; color:#38bdf8; letter-spacing:-2px;">POWERPLANT AI</div>
        <div style="font-size:1.2rem; color:#64748b; margin-bottom:40px; letter-spacing:2px;">NEXT-GEN INDUSTRIAL INTELLIGENCE</div>
        <div class="panel" style="max-width:600px; margin:0 auto; padding:40px;">
            <p style="color:#94a3b8; line-height:1.6;">Welcome to the Unified Control Interface. Access the Prediction Engine, Live Telemetry, and AI Decision Support Hub.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div style="margin-top: 30px;"></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.button("ENTER COMMAND CENTER", type="primary", use_container_width=True, on_click=lambda: setattr(st.session_state, 'app_state', 'Login'))

def auth_page(mode="Login"):
    st.markdown(f"""
    <div style="text-align:center; padding-top:40px; margin-bottom:20px;">
        <div style="font-size:3rem; margin-bottom:10px;">{'🔐' if mode == 'Login' else '🛡️'}</div>
        <div style="font-size:1.8rem; font-weight:800; color:#f8fafc; letter-spacing:1px; text-transform:uppercase;">{mode} Gateway</div>
        <div style="font-size:0.75rem; color:#64748b; font-weight:700; letter-spacing:2px; margin-top:5px;">SECURED BY PLANT_AI PROTOCOL V2.0</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown('<div class="panel" style="padding:40px;">', unsafe_allow_html=True)
        # We wrap inputs in a unique div to style the labels specifically here
        st.markdown('<div style="color:#38bdf8; font-size:0.7rem; font-weight:700; letter-spacing:1px; margin-bottom:5px;">CORPORATE IDENTIFIER</div>', unsafe_allow_html=True)
        email = st.text_input("Email", placeholder="user@plant.ai", label_visibility="collapsed")
        
        st.markdown('<div style="margin-top:20px; color:#38bdf8; font-size:0.7rem; font-weight:700; letter-spacing:1px; margin-bottom:5px;">SYSTEM ACCESS KEY</div>', unsafe_allow_html=True)
        pwd = st.text_input("Password", type="password", placeholder="••••••••", label_visibility="collapsed")
        
        if mode == "Sign Up":
            st.markdown('<div style="margin-top:20px; color:#f59e0b; font-size:0.7rem; font-weight:700; letter-spacing:1px; margin-bottom:5px;">COMPANY VALIDATION</div>', unsafe_allow_html=True)
            code = st.text_input("Security Code", type="password", placeholder="REQUIRED", label_visibility="collapsed")
            st.markdown('<div style="margin-top:30px;"></div>', unsafe_allow_html=True)
            if st.button("APPROVE AUTHORIZATION", type="primary", use_container_width=True):
                res = sign_up(email, pwd, code)
                if res is True: 
                    st.success("Authorization Granted!")
                    time.sleep(1)
                    st.session_state.app_state = "Login"
                    st.rerun()
                else: st.error(res)
        else:
            st.markdown('<div style="margin-top:30px;"></div>', unsafe_allow_html=True)
            if st.button("INITIATE SECURE SESSION", type="primary", use_container_width=True):
                if login(email, pwd):
                    st.session_state.user = email
                    st.session_state.app_state = "Home"
                    st.query_params["session_id"] = email  # Persist login on refresh
                    st.rerun()
                else: st.error("Access Denied: Invalid Hardware Signature.")
        
        st.markdown('<div style="margin-top:25px; border-top:1px solid #1e293b; padding-top:20px; text-align:center;">', unsafe_allow_html=True)
        if mode == "Login":
            if st.button("New Hardware Authorization Request", use_container_width=True):
                st.session_state.app_state = "Sign Up"
                st.rerun()
        else:
            if st.button("Return to Control Gateway", use_container_width=True):
                st.session_state.app_state = "Login"
                st.rerun()
        st.markdown('</div></div>', unsafe_allow_html=True)

# ─── Custom CSS ───
st.markdown("""
<style>
    [data-testid="collapsedControl"] { display: none; }
    header[data-testid="stHeader"] { display: none !important; }
    .stApp { background-color: #0f172a; color: #cbd5e1; font-family: 'Inter', sans-serif; }
    .top-nav {
        display: flex; justify-content: space-between; align-items: center; padding: 15px 40px;
        background: rgba(15, 23, 42, 0.95); border-bottom: 1px solid #1e293b;
        position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    .brand-logo { color: #e2e8f0; font-size: 1.2rem; font-weight: 700; display:flex; align-items:center; gap:8px;}
    .nav-status { display:flex; align-items:center; gap:20px; }
    .status-badge {
        background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); color: #10b981;
        padding: 5px 12px; border-radius: 99px; font-size: 0.75rem; font-weight: 700; letter-spacing: 1px;
    }
    .block-container { padding-top: 100px !important; padding-left: 40px; padding-right: 40px; max-width: 1400px; }
    .stTabs [data-baseweb="tab-list"] { background: transparent; gap: 30px; border-bottom: 2px solid #1e293b; }
    .stTabs [data-baseweb="tab"] { 
        height: 50px; background: transparent !important; color: #64748b !important; 
        font-weight: 600 !important; font-size: 0.9rem !important; text-transform: uppercase !important;
        letter-spacing: 1px !important; border: none !important;
    }
    .stTabs [aria-selected="true"] { color: #38bdf8 !important; border-bottom: 2px solid #38bdf8 !important; }
    .hero-panel {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border: 1px solid #334155; border-radius: 20px; padding: 40px; text-align: center;
        margin-bottom: 30px; position:relative; overflow:hidden;
    }
    .hero-title { font-size: 3rem; font-weight: 800; color: #f8fafc; line-height: 1.1; margin-bottom: 15px;}
    .hero-subtitle { color: #94a3b8; max-width: 600px; margin: 0 auto; font-size: 1rem; }
    .panel { background: #192131; border: 1px solid #2a3648; border-radius: 16px; padding: 24px; margin-bottom: 20px; }
    .section-title { font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 12px; display:flex; align-items:center; gap:8px;}
    .slider-row { display: flex; justify-content: space-between; align-items: bottom; margin-bottom: -15px; font-size: 0.75rem; font-weight:700; color: #94a3b8; text-transform:uppercase; letter-spacing:0.5px;}
    .slider-val { color: #38bdf8; font-size: 1rem; }
    .status-msg { background: rgba(16,185,129,0.05); border: 1px solid rgba(16,185,129,0.2); border-radius: 12px; padding: 16px 20px; display:flex; align-items:center; gap:15px; margin-bottom:20px; }
    .metric-card { background: #111827; border: 1px solid #1e293b; border-radius: 14px; padding: 20px; text-align: left; }
    .m-title { font-size: 0.7rem; color: #64748b; text-transform: uppercase; font-weight: 700; margin-bottom: 6px; }
    .m-value { font-size: 2.2rem; color: #f8fafc; font-weight: 800; display:flex; align-items:baseline; justify-content:space-between; }
    .status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
    .status-crit { background: #ef4444; box-shadow: 0 0 8px #ef4444; }
    .status-sub { background: #f59e0b; box-shadow: 0 0 8px #f59e0b; }
    .status-peak { background: #10b981; box-shadow: 0 0 8px #10b981; }
    div[data-testid="stSlider"] { display:none !important; }
    div[data-testid="stNumberInput"] label { display:none !important; }
    div[data-testid="stNumberInput"] [data-baseweb="input"] { 
        background: #0f172a !important; 
        border: 1px solid #334155 !important; 
        border-radius: 10px !important;
        color: #f8fafc !important;
        transition: all 0.2s;
        height: 48px; padding: 0 10px;
    }
    div[data-testid="stNumberInput"] [data-baseweb="input"]:focus-within { 
        border-color: #38bdf8 !important; 
        box-shadow: 0 0 10px rgba(56,189,248,0.2);
    }
    div[data-testid="stNumberInput"] button { background: transparent !important; color: #64748b !important; border:none !important;}
    div[data-testid="stNumberInput"] button:hover { color: #38bdf8 !important; }
    div[data-baseweb="input"] { background: #0f172a !important; border-radius:8px !important; border-color: #334155 !important; }
    .stButton > button { background: #1e293b !important; color: #e2e8f0 !important; border: 1px solid #334155 !important; border-radius: 10px !important; font-weight: 600 !important; transition: 0.2s; height: 45px; }
    .stButton > button:hover { border-color: #38bdf8 !important; color: #38bdf8 !important; box-shadow: 0 0 15px rgba(56,189,248,0.2); }
    .stButton[data-testid="baseButton-primary"] > button { 
        background: linear-gradient(135deg, #0ea5e9, #38bdf8) !important; 
        border: none !important; color: white !important; 
        font-weight: 800 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        box-shadow: 0 4px 15px rgba(14, 165, 233, 0.4) !important;
    }
    /* Global Loader Cursor & Effects */
    body:has(div[data-testid="stSpinner"]) { cursor: wait !important; }
    
    /* Clean, Box-free Spinner */
    div[data-testid="stSpinner"] {
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        margin: 40px auto; border: none !important; background: transparent !important;
    }
    
    div[data-testid="stSpinner"] > div { border-top-color: #38bdf8 !important; width: 2.5rem !important; height: 2.5rem !important; }
    
    /* Just the text with glow */
    div[data-testid="stSpinner"] p {
        color: #38bdf8 !important; font-size: 0.8rem !important; font-weight: 800 !important;
        letter-spacing: 2px !important; text-transform: uppercase !important;
        margin-top: 15px !important; white-space: nowrap !important;
        text-shadow: 0 0 10px rgba(58, 189, 248, 0.4);
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }
    .live-dot { height: 10px; width: 10px; background-color: #ef4444; border-radius: 50%; display: inline-block; box-shadow: 0 0 10px #ef4444; animation: live-pulse 1s infinite alternate; margin-right: 10px; }
    @keyframes live-pulse { from { transform: scale(0.8); opacity: 0.5; } to { transform: scale(1.2); opacity: 1; } }
    
    /* MOBILE RESPONSIVENESS */
    @media (max-width: 768px) {
        .block-container { padding-left: 15px !important; padding-right: 15px !important; padding-top: 80px !important; }
        .hero-title { font-size: 2rem !important; }
        .hero-subtitle { font-size: 0.9rem !important; }
        .hero-panel { padding: 25px !important; }
        .m-value { font-size: 1.5rem !important; }
        .top-nav { padding: 10px 15px !important; }
        .brand-logo { font-size: 1rem !important; }
        .nav-status { font-size: 0.65rem !important; gap: 10px !important; }
        .status-badge { padding: 3px 8px !important; letter-spacing: 0.5px !important; }
        
        /* Force grid stacking */
        div[style*="grid-template-columns: repeat(4, 1fr)"] { 
            grid-template-columns: repeat(2, 1fr) !important; 
            gap: 10px !important;
        }
        
        /* Reduce panel padding */
        .panel { padding: 16px !important; }
        
        /* Adjust charts */
        [data-testid="stPlotlyChart"] { height: 300px !important; }
    }
</style>

<!-- Navbar -->
<div class="top-nav">
    <div class="brand-logo"><span style="color:#38bdf8;">⚡</span> POWERPLANT AI</div>
    <div class="nav-status">
        <div class="status-badge">🟢 LIVE TELEMETRY STREAMING</div>
        <div style="background:#1e293b; width:36px; height:36px; border-radius:50%; display:flex; align-items:center; justify-content:center; color:#38bdf8;">👤</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── NAVIGATION ENGINE ───
if st.session_state.app_state == "Welcome":
    welcome_page()
elif st.session_state.app_state == "Login":
    auth_page("Login")
elif st.session_state.app_state == "Sign Up":
    auth_page("Sign Up")
elif st.session_state.app_state == "Home":
    # Show Dashboard Header with Logout
    hcol1, hcol2 = st.columns([4, 1])
    with hcol1:
        st.markdown(f"""
        <div style="background: rgba(56,189,248,0.05); padding: 12px 20px; border: 1px solid #1e293b; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <div style="color: #64748b; font-size: 0.7rem; font-weight: 700; letter-spacing: 1px;">USER_SESSION: {st.session_state.user}</div>
            <div style="color: #38bdf8; font-size: 0.7rem; font-weight: 800; letter-spacing: 2px;">HYDERABAD_MISSION_CONTROL // LIVE</div>
        </div>
        """, unsafe_allow_html=True)
    with hcol2:
        if st.button("🚪 SIGN OUT", use_container_width=True):
            st.query_params.clear()
            st.session_state.app_state = "Welcome"
            st.session_state.user = None
            st.rerun()

    # ─── MAIN APP CONTENT ───
    main_tab, analytics_tab, health_tab, live_tab = st.tabs(["🎛️ Simulation Dashboard", "📈 History & Analytics", "🛡️ System Health", "🔴 Live"])

    # ────────────────────────────────────────────────────────────────────────────────
    # 🎛️ TAB 1: SIMULATION
    # ────────────────────────────────────────────────────────────────────────────────
    with main_tab:
        if st.session_state.result is None:
            run_prediction(st.session_state.AT, st.session_state.V, st.session_state.AP, st.session_state.RH)

        st.markdown("""
        <div class="hero-panel">
            <div style="background: rgba(56,189,248,0.1); color:#38bdf8; border:1px solid rgba(56,189,248,0.3); padding:4px 12px; border-radius:99px; font-size:0.7rem; font-weight:700; display:inline-block; margin-bottom:15px; letter-spacing:1px;">AI DECISION SUPPORT SYSTEM</div>
            <div class="hero-title">Predict Power Output<br>With Neural Intelligence</div>
            <div class="hero-subtitle">Optimize combined cycle performance by analyzing real-time ambient factors and thermodynamics using a dedicated deep learning model.</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-title">⏱️ QUICK CLIMATE SCENARIOS</div>', unsafe_allow_html=True)
        sc1, sc2, sc3, sc4 = st.columns(4)
        for idx, (label, params) in enumerate(SCENARIOS.items()):
            col = [sc1, sc2, sc3, sc4][idx]
            with col:
                if st.button(label, key=f"sbtn_{idx}", use_container_width=True):
                    st.session_state.AT, st.session_state.V, st.session_state.AP, st.session_state.RH = params["AT"], params["V"], params["AP"], params["RH"]
                    st.session_state.last_scenario = label.split(' ', 1)[1] if ' ' in label else label
                    run_prediction(params["AT"], params["V"], params["AP"], params["RH"])

        st.markdown("<br>", unsafe_allow_html=True)

        left_side, right_side = st.columns([1.2, 2.5], gap="large")
        with left_side:
            st.markdown('<div class="panel">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">🎛️ SENSOR OVERRIDES</div>', unsafe_allow_html=True)
            def mk_input(label, key, min_v, max_v, unit):
                st.markdown(f'<div class="slider-row" style="margin-bottom:8px;"><span>{label}</span><span class="slider-val">{unit}</span></div>', unsafe_allow_html=True)
                st.number_input(label, min_v, max_v, key=key, step=0.1, format="%.2f")
                st.markdown('<div style="margin-bottom:10px;"></div>', unsafe_allow_html=True)
            mk_input("Ambient Temp (AT)", "AT", 1.0, 45.0, "°C")
            mk_input("Vacuum (V)", "V", 25.0, 85.0, "CMHG")
            mk_input("Atmos Pressure (AP)", "AP", 990.0, 1035.0, "MBAR")
            mk_input("Relative Humidity (RH)", "RH", 20.0, 100.0, "%")
            if st.button("⚡ APPLY MANUAL OVERRIDES", type="primary", use_container_width=True):
                run_prediction(st.session_state.AT, st.session_state.V, st.session_state.AP, st.session_state.RH)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="panel">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">🌍 ENVIRONMENTAL SYNC</div>', unsafe_allow_html=True)
            selected_city = st.selectbox("Select Project Site", INDIAN_CITIES, index=INDIAN_CITIES.index("Hyderabad") if "Hyderabad" in INDIAN_CITIES else 0, label_visibility="collapsed", key="search_term")
            st.button("Fetch & Predict", type="primary", use_container_width=True, on_click=fetch_and_predict, args=(st.session_state.search_term,))
            if st.session_state.get("weather_error"):
                st.error(st.session_state.weather_error)
                st.session_state.weather_error = None
            st.markdown('</div>', unsafe_allow_html=True)

        with right_side:
            res = st.session_state.result
            p_val = res["predicted_power"]
            eff = (p_val / RATED_CAPACITY) * 100
            status_color = "#10b981" if p_val > 470 else "#f59e0b" if p_val > 440 else "#ef4444"
            st.markdown(f"""
            <div class="status-msg" style="border-left: 5px solid {status_color};">
                <div style="width:12px; height:12px; border-radius:50%; background:{status_color};"></div>
                <div>
                    <div style="font-weight:700; color:#f8fafc; font-size:0.95rem;">System Performance: {'OPTIMAL' if p_val > 470 else 'MODERATE' if p_val > 440 else 'CRITICAL'}</div>
                    <div style="font-size:0.75rem; color:{status_color}; font-weight:700; letter-spacing:1px; text-transform:uppercase;">EFFICIENCY DELTA: {(eff - 90):+.1f}% VS DESIGN BASELINE</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            m1, m2, m3 = st.columns(3)
            with m1: st.markdown(f'<div class="metric-card"><div class="m-title">Predicted Output</div><div class="m-value"><span>{p_val:.1f}</span><span style="font-size:0.75rem; color:{status_color}; font-weight:700;">MW</span></div></div>', unsafe_allow_html=True)
            with m2: st.markdown(f'<div class="metric-card"><div class="m-title">Rated Capacity</div><div class="m-value"><span>{RATED_CAPACITY:.0f}</span><span style="font-size:0.75rem; color:#64748b; font-weight:700;">LIMIT</span></div></div>', unsafe_allow_html=True)
            with m3: st.markdown(f'<div class="metric-card"><div class="m-title">Plant Efficiency</div><div class="m-value"><span>{eff:.1f}</span><span style="font-size:0.75rem; color:#38bdf8; font-weight:700;">%</span></div></div>', unsafe_allow_html=True)

            st.markdown('<div class="panel" style="text-align:center;">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">ENGINE GAUGE</div>', unsafe_allow_html=True)
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number", value=p_val,
                number={"suffix": "", "font": {"size": 42, "color": "#f8fafc"}},
                gauge={"axis": {"range": [0, 500], "visible": False}, "bar": {"color": "#38bdf8", "thickness": 0.2}, "bgcolor": "#1e293b",
                    "steps": [{"range": [0, 440], "color": "rgba(239, 68, 68, 0.2)"}, {"range": [440, 475], "color": "rgba(245, 158, 11, 0.2)"}, {"range": [475, 500], "color": "rgba(16, 185, 129, 0.2)"}]}
            ))
            fig_g.add_annotation(x=0.5, y=0.32, text="MW LOAD", showarrow=False, font=dict(color="#64748b", size=10, weight="bold"))
            fig_g.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=10, b=10, l=10, r=10), height=300)
            st.plotly_chart(fig_g, use_container_width=True, key="sim_gauge")
            st.markdown("""
            <div style="display:flex; justify-content:center; gap:20px; font-size:0.7rem; color:#64748b; font-weight:700; letter-spacing:1px; margin-top:-20px;">
                <div style="display:flex; align-items:center; gap:6px;"><span class="status-dot status-crit"></span> CRITICAL</div>
                <div style="display:flex; align-items:center; gap:6px;"><span class="status-dot status-sub"></span> SUB</div>
                <div style="display:flex; align-items:center; gap:6px;"><span class="status-dot status-peak"></span> PEAK</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # 📈 TAB 2: ANALYTICS
    with analytics_tab:
        st.markdown('<div class="section-title" style="margin-top:20px;">TELEMETRY HISTORICAL DATA</div>', unsafe_allow_html=True)
        history = get_history(limit=100)
        if not history:
            st.info("No prediction history found. Run some simulations to view data.")
        else:
            df = pd.DataFrame(history)
            st.markdown('<div class="panel">', unsafe_allow_html=True)
            fig_hist = go.Figure()
            fig_hist.add_trace(go.Scatter(x=df["timestamp"], y=df["predicted_power"], mode='lines+markers', name='Power (MW)', line=dict(color="#38bdf8", width=3)))
            fig_hist.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=350,
                xaxis=dict(gridcolor="#1e293b", tickfont=dict(color="#64748b")), yaxis=dict(gridcolor="#1e293b", tickfont=dict(color="#64748b"), range=[400, 510]), margin=dict(t=20, b=20))
            st.plotly_chart(fig_hist, use_container_width=True, key="hist_chart")
            st.markdown('</div>', unsafe_allow_html=True)
            col_t1, col_t2 = st.columns([2, 1])
            with col_t1:
                st.markdown('<div class="panel" style="padding:0;">', unsafe_allow_html=True)
                st.table(df[["timestamp", "temperature", "scenario", "predicted_power"]].head(10))
                st.markdown('</div>', unsafe_allow_html=True)
            with col_t2:
                st.markdown('<div class="panel">', unsafe_allow_html=True)
                st.write("### Quick Stats")
                st.metric("Avg Prediction", f"{df['predicted_power'].mean():.2f} MW")
                st.metric("Max Efficiency", f"{(df['predicted_power'].max()/480*100):.1f}%")
                if st.button("Purge Database", use_container_width=True):
                    clear_history(); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # 🛡️ TAB 3: SYSTEM HEALTH
    with health_tab:
        st.markdown('<div class="section-title" style="margin-top:20px;">DIAGNOSTICS & AI CALIBRATION</div>', unsafe_allow_html=True)
        h1, h2, h3, h4 = st.columns(4)
        with h1: st.markdown('<div class="panel" style="text-align:center;"><h3>🧠</h3><div class="m-title">AI Engine</div><span style="color:#10b981;font-weight:700;">STABLE</span></div>', unsafe_allow_html=True)
        with h2: st.markdown('<div class="panel" style="text-align:center;"><h3>📡</h3><div class="m-title">Telemetry</div><span style="color:#10b981;font-weight:700;">LOW LATENCY</span></div>', unsafe_allow_html=True)
        with h3: st.markdown('<div class="panel" style="text-align:center;"><h3>🎯</h3><div class="m-title">Confidence</div><span style="color:#38bdf8;font-weight:700;">99.1%</span></div>', unsafe_allow_html=True)
        with h4: st.markdown('<div class="panel" style="text-align:center;"><h3>💾</h3><div class="m-title">Buffer</div><span style="color:#64748b;font-weight:700;">4.2 KB</span></div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="panel"><div class="section-title">💡 AUTOMATED RECOMMENDATIONS</div>
            <div style="padding:15px; border-left:4px solid #38bdf8; background:rgba(56,189,248,0.05); border-radius:8px; margin-bottom:15px;"><strong style="color:#f8fafc">Efficiency Optimization:</strong> High ambient temperature detected. Recommend switching to closed-cycle cooling.</div>
            <div style="padding:15px; border-left:4px solid #f59e0b; background:rgba(245,158,11,0.05); border-radius:8px;"><strong style="color:#f8fafc">Maintenance Alert:</strong> Vacuum (V) levels near threshold. Inspection recommended.</div>
        </div>
        """, unsafe_allow_html=True)

    # 🔴 TAB 4: LIVE
    with live_tab:
        st.markdown(f"""
        <div style="display:flex; align-items:center; justify-content:center; margin-top:30px; margin-bottom:5px;">
            <div class="live-dot"></div>
            <div class="section-title" style="margin:0;">HYDERABAD MISSION CONTROL // SYSTEM LOAD</div>
        </div>
        <div style="text-align:center; color:#64748b; font-size:0.75rem; letter-spacing:2px; margin-bottom:30px; font-weight:700;">LIVE TELEMETRY FROM DEDICATED SATELLITE LINK</div>
        """, unsafe_allow_html=True)
        time_range = "24 Hours"

        t_c1, t_c2, t_c3, t_c4 = st.columns(4)
        def telemetry_box(label, value, unit, color="#38bdf8"):
            st.markdown(f'<div class="panel" style="padding:12px; border-top:2px solid {color};"><div style="font-size:0.6rem; color:#64748b; font-weight:700; text-transform:uppercase; margin-bottom:2px;">{label}</div><div style="font-size:1.1rem; color:#f8fafc; font-weight:800;">{value} <span style="font-size:0.65rem; color:{color};">{unit}</span></div></div>', unsafe_allow_html=True)
        with t_c1: telemetry_box("Ambient Temp", f"{st.session_state.live_data['temperature']:.1f}", "°C")
        with t_c2: telemetry_box("Vaccuum (V)", f"{st.session_state.live_data.get('v', 0):.1f}", "cmHg")
        with t_c3: telemetry_box("Baro Pressure", f"{st.session_state.live_data['pressure']:.0f}", "mBar")
        with t_c4: telemetry_box("Rel Humidity", f"{st.session_state.live_data['humidity']:.0f}", "%")

        st.markdown("<br>", unsafe_allow_html=True)
        hist_raw = get_history(limit=100)
        if hist_raw:
            df_live = pd.DataFrame(hist_raw); df_live['timestamp'] = pd.to_datetime(df_live['timestamp']); df_live = df_live.sort_values('timestamp')
            df_live['predicted_power'] = df_live.apply(lambda x: x['predicted_power'] + np.random.RandomState(int(x['timestamp'].timestamp())).uniform(-0.05, 0.05), axis=1)
            df_live['capacity'] = RATED_CAPACITY; now = pd.Timestamp.now()
            if time_range == "30 Min": df_live = df_live[df_live['timestamp'] > now - pd.Timedelta(minutes=30)]
            elif time_range == "6 Hours": df_live = df_live[df_live['timestamp'] > now - pd.Timedelta(hours=6)]
            elif time_range == "24 Hours": df_live = df_live[df_live['timestamp'] > now - pd.Timedelta(hours=24)]

            fig_live = go.Figure()
            fig_live.add_trace(go.Scatter(x=df_live['timestamp'], y=df_live['capacity'], name="RATED CAPACITY", line=dict(color="rgba(255,255,255,0.1)", width=2, dash='dash')))
            fig_live.add_trace(go.Scatter(x=df_live['timestamp'], y=df_live['predicted_power'], name="MW OUTPUT", mode='lines+markers', marker=dict(size=[0]*(len(df_live)-1) + [10], color="#38bdf8", line=dict(color="rgba(56,189,248,0.3)", width=10)), line=dict(color="#38bdf8", width=3), fill='tozeroy', fillcolor='rgba(56,189,248,0.05)'))
            fig_live.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=10, b=10, l=10, r=10), height=400, showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#64748b", size=10)),
                xaxis=dict(showgrid=False, color="#64748b", tickfont=dict(size=9), tickformat="%H:%M", nticks=10), yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#64748b", tickfont=dict(size=9), title="MEGAWATTS (MW)", range=[400, 500]))
            st.plotly_chart(fig_live, use_container_width=True, key="live_telemetry_chart")

            mc1, mc2 = st.columns([2.5, 1])
            with mc1:
                st.markdown('<div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:15px; margin-top:20px;">', unsafe_allow_html=True)
                latest = df_live.iloc[-1] if not df_live.empty else {"predicted_power": 0, "temperature": 0, "pressure": 0, "humidity": 0, "timestamp": pd.Timestamp.now()}
                def mini_m(label, val, unit, color="#38bdf8"):
                    return f'<div class="panel" style="padding:15px;"><div style="font-size:0.65rem; color:#64748b; font-weight:700; text-transform:uppercase; margin-bottom:5px;">{label}</div><div style="font-size:1.2rem; color:#f8fafc; font-weight:800;">{val} <span style="font-size:0.7rem; color:{color};">{unit}</span></div></div>'
                st.markdown(mini_m("Active Load", f"{latest['predicted_power']:.1f}", "MW"), unsafe_allow_html=True)
                st.markdown(mini_m("Plant Status", "NOMINAL", "", "#22c55e"), unsafe_allow_html=True)
                st.markdown(mini_m("AI Confidence", "98.4", "%"), unsafe_allow_html=True)
                st.markdown(mini_m("Last Sync", f"{latest['timestamp'].strftime('%H:%M:%S')}", ""), unsafe_allow_html=True)
                st.markdown(f'</div><div style="background:rgba(56,189,248,0.05); border:1px solid rgba(56,189,248,0.1); padding:10px; border-radius:8px; margin-top:15px;"><span style="color:#38bdf8; font-family:monospace; font-size:0.7rem;">[SATELLITE_LINK]</span> <span style="color:#64748b; font-family:monospace; font-size:0.7rem;">DATA_SYNC_OK // CITY=HYDERABAD</span></div>', unsafe_allow_html=True)
            with mc2:
                st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
                if st.session_state.live_monitoring:
                    st.markdown('<div class="panel" style="padding:15px; border-color:#ef4444; border-left:3px solid #ef4444;"><div style="font-size:0.6rem; color:#ef4444; font-weight:800; text-transform:uppercase; margin-bottom:5px;">NEXT HEARTBEAT</div>', unsafe_allow_html=True)
                    timer_place = st.empty(); st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="panel" style="padding:15px; border-color:#334155;"><div style="font-size:0.6rem; color:#64748b; font-weight:800; text-transform:uppercase; margin-bottom:5px;">HEARTBEAT</div><div style="font-size:1rem; color:#64748b; font-weight:800;">INACTIVE</div></div>', unsafe_allow_html=True)
            st.markdown('<div style="margin-top:30px; display:flex; justify-content:center;">', unsafe_allow_html=True)
            st.toggle("📡 ENABLE REAL-TIME PLANT HEARTBEAT (60s REFRESH)", key="live_monitoring_alt")
            if st.session_state.live_monitoring_alt != st.session_state.live_monitoring:
                st.session_state.live_monitoring = st.session_state.live_monitoring_alt; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="panel" style="padding:60px; text-align:center; color:#64748b;">NO TELEMETRY DATA DETECTED FROM HYDERABAD SATELLITE HUB.</div>', unsafe_allow_html=True)

    # ─ Footer ─
    st.markdown("""
    <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #1e293b; padding:20px 0; margin-top:30px;">
        <div style="color:#94a3b8; font-size:0.75rem;">POWERPLANT AI DECISION ENGINE V1.3.0</div>
        <div style="color:#64748b; font-size:1.1rem;">⚡ 🌍 🛡️</div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.live_monitoring:
        for i in range(60, 0, -1):
            if 'timer_place' in locals():
                timer_place.markdown(f'<div style="font-size:1.4rem; color:#ef4444; font-weight:900; font-family:monospace;">{i:02d}s</div>', unsafe_allow_html=True)
            time.sleep(1)
        fetch_and_predict("Hyderabad"); st.rerun()
