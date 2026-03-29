
const API_BASE = "http://localhost:8000";

// ── Tab switching ────────────────────────────────────────────────────────────
function switchTab(tab) {
    document.querySelectorAll(".tab").forEach(t => {
        t.classList.remove("active");
        t.setAttribute("aria-selected", "false");
    });
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));

    document.getElementById(`tab-${tab}`).classList.add("active");
    document.getElementById(`tab-${tab}`).setAttribute("aria-selected", "true");
    document.getElementById(`panel-${tab}`).classList.add("active");

    // Hide results from previous tab
    hideResult();
    hideError();
}

// ── Manual Prediction ────────────────────────────────────────────────────────
async function predictManual() {
    const AT = parseFloat(document.getElementById("AT").value);
    const V = parseFloat(document.getElementById("V").value);
    const AP = parseFloat(document.getElementById("AP").value);
    const RH = parseFloat(document.getElementById("RH").value);

    if ([AT, V, AP, RH].some(isNaN)) {
        showError("Please fill in all four sensor fields before predicting.");
        return;
    }

    hideError();
    hideResult();
    showLoader("Running ANN prediction…");

    try {
        const res = await fetch(`${API_BASE}/predict`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ AT, V, AP, RH })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || `Server error ${res.status}`);
        }

        const data = await res.json();
        hideLoader();
        showResult(data, null);
    } catch (e) {
        hideLoader();
        showError(e.message);
    }
}

// ── Weather Prediction ───────────────────────────────────────────────────────
async function predictWeather() {
    const city = document.getElementById("city").value.trim();

    if (!city) {
        showError("Please enter a city name.");
        return;
    }

    hideError();
    hideResult();
    hideWeatherCards();
    showLoader(`Fetching weather for "${city}"…`);

    try {
        const res = await fetch(`${API_BASE}/weather-prediction?city=${encodeURIComponent(city)}`);

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || `Server error ${res.status}`);
        }

        const data = await res.json();
        hideLoader();
        showWeatherCards(data);
        showResult(data, data.city);
    } catch (e) {
        hideLoader();
        showError(e.message);
    }
}

// ── Weather Cards display ────────────────────────────────────────────────────
function showWeatherCards(data) {
    document.getElementById("wv-temp").textContent = data.temperature;
    document.getElementById("wv-hum").textContent = data.humidity;
    document.getElementById("wv-pres").textContent = data.pressure;
    document.getElementById("wv-vac").textContent = data.estimated_vacuum ?? "N/A";
    document.getElementById("weather-cards").classList.remove("hidden");
}

function hideWeatherCards() {
    document.getElementById("weather-cards").classList.add("hidden");
}

// ── Result display ───────────────────────────────────────────────────────────
function showResult(data, city) {
    const power = data.predicted_power;
    const rated = data.rated_capacity || 480;
    const deviation = data.deviation;
    const pct = Math.min((power / rated) * 100, 100);
    const efficiency = ((power / rated) * 100).toFixed(1);

    // Animate counter
    animateNumber("result-power", 0, power, 1200, 2);

    // Gauge fill after short delay
    setTimeout(() => {
        document.getElementById("gauge-fill").style.width = pct + "%";
    }, 200);

    // City label
    const cityEl = document.getElementById("result-city");
    cityEl.textContent = city ? `📍 ${city}` : "Manual Input";

    // Stats
    document.getElementById("stat-rated").textContent = `${rated} MW`;
    document.getElementById("stat-deviation").textContent = `${deviation} MW`;
    document.getElementById("stat-efficiency").textContent = `${efficiency}%`;

    // Status pill
    const statusEl = document.getElementById("result-status");
    if (pct >= 90) {
        statusEl.textContent = "✅ Optimal Output — Plant running at peak performance";
        statusEl.className = "result-status status-good";
    } else if (pct >= 70) {
        statusEl.textContent = "⚠️ Moderate Output — Conditions slightly affecting performance";
        statusEl.className = "result-status status-warning";
    } else {
        statusEl.textContent = "🔴 Low Output — Significant deviation from rated capacity";
        statusEl.className = "result-status status-danger";
    }

    document.getElementById("result-section").classList.remove("hidden");

    // Scroll into view
    document.getElementById("result-section").scrollIntoView({ behavior: "smooth", block: "start" });
}

function hideResult() {
    document.getElementById("result-section").classList.add("hidden");
    document.getElementById("gauge-fill").style.width = "0%";
}

// ── Error / Loader helpers ───────────────────────────────────────────────────
function showError(msg) {
    document.getElementById("error-message").textContent = msg;
    document.getElementById("error-banner").classList.remove("hidden");
}

function hideError() {
    document.getElementById("error-banner").classList.add("hidden");
}

function showLoader(text) {
    document.getElementById("loader-text").textContent = text;
    document.getElementById("loader").classList.remove("hidden");
}

function hideLoader() {
    document.getElementById("loader").classList.add("hidden");
}

// ── Animated number counter ──────────────────────────────────────────────────
function animateNumber(id, from, to, duration, decimals) {
    const el = document.getElementById(id);
    const start = performance.now();
    function step(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = easeOutCubic(progress);
        const value = from + (to - from) * eased;
        el.textContent = value.toFixed(decimals);
        if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}

function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
}
