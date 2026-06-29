from flask import Flask, render_template, jsonify, request
import random

app = Flask(__name__)

# ─────────────────────────────────────────────────────────────────────────
# VEHICLE DATABASE
#
# Specs are drawn from manufacturer-published figures (India models, via
# CarWale, June 2026) and the EV Database (Europe, June 2026). Range figures
# for India use the certified MIDC test-cycle number, not real-world range,
# so the derived efficiency (Wh/km) will read a little optimistic compared
# to the European WLTP-based numbers — that's expected and kept as-is so
# the two datasets stay internally honest about what they actually measure.
#
# voltage_nominal is not published by either source for most models, so it
# is inferred from the vehicle's known battery platform (e.g. Mahindra's
# INGLO and Hyundai/Kia's E-GMP are documented 800V architectures; most
# other mainstream packs are conventional ~350-400V). Treat it as a
# reasonable engineering estimate, not a verified datasheet value.
# ─────────────────────────────────────────────────────────────────────────

def _car(name, market, segment, battery_kwh, range_km, fastcharge_kw,
         voltage_nominal, price):
    return {
        "name": name,
        "market": market,
        "segment": segment,
        "battery_kwh": battery_kwh,
        "range_km": range_km,
        "efficiency_wh_km": round(battery_kwh * 1000 / range_km, 1),
        "fastcharge_kw": fastcharge_kw,
        "voltage_nominal": voltage_nominal,
        "price": price,
    }


CARS = {
    # ---- India (CarWale, June 2026) — range is certified MIDC figure ----
    "tata_tiago_ev":      _car("Tata Tiago EV",          "India", "Hatchback", 24.0, 315, 50,  320, "₹9.99 Lakh"),
    "tata_punch_ev":      _car("Tata Punch EV",           "India", "Compact SUV", 35.0, 421, 70,  350, "₹12.59 Lakh"),
    "tata_nexon_ev":      _car("Tata Nexon EV",           "India", "SUV",       45.1, 465, 50,  350, "₹17.49 Lakh"),
    "tata_curvv_ev":      _car("Tata Curvv EV",           "India", "SUV Coupe", 55.0, 502, 70,  380, "₹19.49 Lakh"),
    "tata_harrier_ev":    _car("Tata Harrier EV",         "India", "SUV",       75.0, 627, 120, 400, "₹30.23 Lakh"),
    "mahindra_be6":       _car("Mahindra BE 6",           "India", "SUV Coupe", 79.0, 682, 175, 800, "₹28.49 Lakh"),
    "mahindra_xev9e":     _car("Mahindra XEV 9e",         "India", "SUV",       79.0, 656, 175, 800, "₹31.25 Lakh"),
    "mahindra_xev9s":     _car("Mahindra XEV 9S",         "India", "SUV",       59.0, 542, 140, 800, "₹30.20 Lakh"),
    "mg_windsor_ev":      _car("MG Windsor EV",           "India", "Crossover", 52.9, 460, 50,  380, "₹16.10 Lakh"),
    "mg_comet_ev":        _car("MG Comet EV",             "India", "Hatchback", 17.3, 230, 3.3, 320, "₹8.82 Lakh"),
    "mg_cyberster":       _car("MG Cyberster",            "India", "Convertible", 77.0, 580, 144, 400, "₹77.50 Lakh"),
    "maruti_e_vitara":    _car("Maruti Suzuki e Vitara",  "India", "SUV",       61.0, 500, 70,  400, "₹17.26 Lakh"),
    "byd_atto3_in":       _car("BYD Atto 3",              "India", "SUV",       60.48, 521, 80, 400, "₹33.99 Lakh"),
    "hyundai_creta_ev":   _car("Hyundai Creta Electric",  "India", "SUV",       51.4, 473, 50,  400, "₹24.70 Lakh"),
    "vinfast_vf6":        _car("VinFast VF 6",            "India", "SUV",       59.6, 480, 120, 400, "₹19.19 Lakh"),
    "vinfast_vf7":        _car("VinFast VF 7",            "India", "SUV",       75.3, 510, 120, 400, "₹26.79 Lakh"),

    # ---- Europe (EV Database, June 2026) — range is WLTP figure ----
    "renault_twingo":     _car("Renault Twingo E-Tech 27.5kWh", "Europe", "A Hatchback", 27.5, 185, 40,  400, "€19,990"),
    "fiat_500e":          _car("Fiat 500e Hatchback",       "Europe", "B Hatchback", 37.3, 235, 65,  400, "€34,990"),
    "renault_5":          _car("Renault 5 E-Tech 52kWh",    "Europe", "B Hatchback", 52.0, 335, 75,  400, "€32,900"),
    "byd_dolphin_surf":   _car("BYD Dolphin Surf 43.2kWh",  "Europe", "B Hatchback", 43.2, 265, 60,  400, "€30,990"),
    "mg4_electric":       _car("MG MG4 Electric 64kWh",     "Europe", "C Hatchback", 61.7, 360, 107, 400, "€39,990"),
    "vw_id3_neo":         _car("Volkswagen ID.3 Neo 79kWh", "Europe", "C Hatchback", 79.0, 490, 135, 400, "€44,995"),
    "hyundai_kona_ev":    _car("Hyundai Kona Electric 65kWh","Europe", "B SUV",      65.4, 390, 79,  400, "€47,190"),
    "volvo_ex30":         _car("Volvo EX30 Single Motor ER","Europe", "B SUV",      65.0, 365, 101, 400, "€44,990"),
    "kia_ev3":            _car("Kia EV3 Long Range",        "Europe", "B SUV",      78.0, 455, 105, 400, "€41,390"),
    "hyundai_ioniq5":     _car("Hyundai IONIQ 5 84kWh RWD", "Europe", "C SUV",      80.0, 450, 196, 800, "€51,650"),
    "kia_ev6":            _car("Kia EV6 Long Range AWD",    "Europe", "C SUV",      80.0, 440, 205, 800, "€53,990"),
    "tesla_model3_rwd":   _car("Tesla Model 3 RWD",         "Europe", "D Sedan",    60.0, 450, 110, 400, "€37,970"),
    "tesla_modely_rwd":   _car("Tesla Model Y RWD",         "Europe", "D SUV",      60.0, 380, 110, 400, "€40,970"),
    "bmw_i4":             _car("BMW i4 eDrive40",           "Europe", "D Liftback", 80.7, 515, 112, 400, "€59,200"),
    "mercedes_cla250":    _car("Mercedes-Benz CLA 250+",    "Europe", "D Sedan",    85.0, 585, 208, 800, "€55,728"),
    "skoda_enyaq":        _car("Skoda Enyaq iV 80",         "Europe", "C SUV",      77.0, 440, 124, 400, "€48,900"),
    "audi_q6_etron":      _car("Audi Q6 e-tron quattro",    "Europe", "D SUV",      94.9, 480, 186, 800, "€74,700"),
    "byd_seal":           _car("BYD Seal 82.5kWh AWD",      "Europe", "D Sedan",    82.5, 445, 100, 400, "€52,990"),
    "volvo_ex60":         _car("Volvo EX60 P12 AWD",        "Europe", "D SUV",      112.0, 610, 250, 800, "€71,990"),
    "lucid_air_gt":       _car("Lucid Air Grand Touring",   "Europe", "F Sedan",    117.0, 720, 190, 924, "€130,900"),
    "mercedes_eqs":       _car("Mercedes-Benz EQS 450+",    "Europe", "F Sedan",    118.0, 685, 160, 400, "€109,551"),
    "rolls_royce_spectre":_car("Rolls-Royce Spectre",       "Europe", "F Coupe",    102.0, 465, 126, 400, "€379,015"),
}

DEFAULT_CAR_ID = "tata_nexon_ev"

# Each /data poll simulates this many seconds of real operation
TICK_SECONDS = 4
TICK_HOURS = TICK_SECONDS / 3600.0

# Typical AC (non-fast) home/public charging power, in kW
AC_CHARGE_KW = 7.4


def baseline_state(car_id):
    car = CARS[car_id]
    return {
        "car_id":        car_id,
        "soc":           45.0,
        "voltage":       float(car["voltage_nominal"]),
        "current":       0.0,
        "temperature":   28.0,
        "soh":           92.0,
        "rul":           850,
        "cycles":        0,
        "fast_charge":   0.0,        # effective C-rate of most recent charge
        "charge_mode":   "normal",   # "normal" (AC) or "fast" (DC)
        "command":       "idle",
        "health_score":  88,
        "cell_imbalance": 1.2,
        "coulombic_eff": 97.5,
        "avg_speed":     60.0,
        "power_kw":      0.0,
    }


battery = baseline_state(DEFAULT_CAR_ID)


def active_car():
    return CARS[battery["car_id"]]


# ─────────────────────────────────────────────
# FORMULA-BASED ML REPLACEMENT
# ─────────────────────────────────────────────
def predict_soh():
    b = battery
    soh = (100
           - b["cycles"] * 0.018
           - (b["temperature"] - 25) * 0.15
           - b["fast_charge"] * 8
           - b["cell_imbalance"] * 1.2
           + random.uniform(-0.5, 0.5))
    return round(max(50, min(100, soh)), 1)

def predict_rul():
    soh = battery["soh"]
    rul = ((soh - 70) / 0.018
           - battery["fast_charge"] * 200
           - (battery["temperature"] - 25) * 10
           + random.uniform(-10, 10))
    return int(max(0, min(1500, rul)))

# ─────────────────────────────────────────────
# UPDATE BATTERY STATE (now vehicle-aware)
# ─────────────────────────────────────────────
def update_battery():
    b = battery
    car = active_car()
    capacity_kwh = car["battery_kwh"]
    nominal_v = car["voltage_nominal"]
    cmd = b["command"]

    if cmd == "charge":
        charge_power_kw = car["fastcharge_kw"] if b["charge_mode"] == "fast" \
            else min(AC_CHARGE_KW, car["fastcharge_kw"])
        delta_soc = (charge_power_kw * TICK_HOURS / capacity_kwh) * 100
        b["soc"] = min(b["soc"] + delta_soc, 100)
        b["power_kw"] = round(charge_power_kw, 1)
        b["current"] = round(charge_power_kw * 1000 / max(b["voltage"], 1), 1)
        b["fast_charge"] = round(min(charge_power_kw / capacity_kwh, 1.0), 2)
        b["temperature"] += 0.08 * (1 + b["fast_charge"])
        if b["soc"] >= 100:
            b["command"] = "idle"

    elif cmd == "discharge":
        drive_power_kw = (car["efficiency_wh_km"] * b["avg_speed"]) / 1000.0
        delta_soc = (drive_power_kw * TICK_HOURS / capacity_kwh) * 100
        b["soc"] = max(b["soc"] - delta_soc, 0)
        b["power_kw"] = round(drive_power_kw, 1)
        b["current"] = round(-drive_power_kw * 1000 / max(b["voltage"], 1), 1)
        b["temperature"] += 0.05
        if b["soc"] <= 0:
            b["command"] = "idle"

    else:
        b["current"] = 0
        b["power_kw"] = 0
        b["temperature"] = max(b["temperature"] - 0.03, 25 + random.uniform(-1, 1))

    # Voltage sags toward the bottom of SOC and rises toward the top,
    # scaled to this vehicle's own nominal pack voltage.
    v_span = nominal_v * 0.22
    b["voltage"] = round(
        nominal_v - v_span / 2 + (b["soc"] / 100) * v_span
        + random.uniform(-nominal_v * 0.004, nominal_v * 0.004), 1)
    b["temperature"] = round(min(b["temperature"], 60), 1)
    b["soh"] = predict_soh()
    b["rul"] = predict_rul()

    b["health_score"] = int(
        b["soh"] * 0.5
        + (100 - b["temperature"]) * 0.2
        + b["coulombic_eff"] * 0.2
        + (100 - b["cell_imbalance"] * 10) * 0.1
    )
    b["health_score"] = max(0, min(100, b["health_score"]))

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/cars')
def cars():
    return jsonify([{"id": cid, **spec} for cid, spec in CARS.items()])

@app.route('/select_car', methods=['POST'])
def select_car():
    data = request.json or {}
    car_id = data.get("car_id")
    if car_id not in CARS:
        return jsonify({"status": "error", "message": "unknown car_id"}), 400
    battery.update(baseline_state(car_id))
    return jsonify({"status": "ok", "car": {"id": car_id, **CARS[car_id]}})

@app.route('/data')
def data():
    update_battery()
    b = battery
    car = active_car()

    if b["temperature"] > 50:
        alert = "🔴 CRITICAL: Battery overheating!"
    elif b["soc"] < 15:
        alert = "🟡 WARNING: Low battery — charge soon"
    elif b["soh"] < 75:
        alert = "🟠 WARNING: Battery health degraded"
    else:
        alert = "🟢 All systems normal"

    status = ("CHARGING"    if b["command"] == "charge"
         else "DISCHARGING" if b["command"] == "discharge"
         else "IDLE")

    return jsonify({
        "soc"           : round(b["soc"], 1),
        "voltage"       : b["voltage"],
        "current"       : round(b["current"], 1),
        "temperature"   : b["temperature"],
        "soh"           : b["soh"],
        "rul"           : b["rul"],
        "cycles"        : b["cycles"],
        "health_score"  : b["health_score"],
        "power_kw"      : b["power_kw"],
        "status"        : status,
        "alert"         : alert,
        "cell_imbalance": b["cell_imbalance"],
        "coulombic_eff" : b["coulombic_eff"],
        "charge_mode"   : b["charge_mode"],
        "avg_speed"     : b["avg_speed"],
        "car"           : {"id": b["car_id"], **car},
    })

@app.route('/cmd', methods=['POST'])
def cmd():
    data = request.json or {}
    c = data.get("cmd", "idle")
    battery["command"] = c
    if c == "charge":
        battery["charge_mode"] = "fast" if data.get("fast") else "normal"
        battery["cycles"] += 1
    if c == "discharge" and "speed" in data:
        try:
            battery["avg_speed"] = max(5.0, min(180.0, float(data["speed"])))
        except (TypeError, ValueError):
            pass
    return jsonify({"status": "ok"})

@app.route('/reset', methods=['POST'])
def reset():
    battery.update(baseline_state(battery["car_id"]))
    return jsonify({"status": "reset"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
