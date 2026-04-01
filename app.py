from flask import Flask, jsonify, redirect, render_template, request, url_for
import config
from db import init_db, get_summary
from sync import log_trip, parse_car
from ors import ORSError, autocomplete

app = Flask(__name__)

init_db()

MODES = ["bike", "walk", "train", "bus", "scooter", "other"]


@app.route("/")
def index():
    summary = get_summary()
    logged      = request.args.get("logged")
    error       = request.args.get("error")
    round_trip  = request.args.get("round_trip")
    return render_template(
        "index.html",
        summary=summary,
        config_cars=config.CARS,
        modes=MODES,
        logged=logged,
        error=error,
        round_trip=round_trip,
    )


@app.route("/log", methods=["POST"])
def log():
    date        = request.form.get("date", "").strip()
    start       = request.form.get("start", "").strip()
    end         = request.form.get("end", "").strip()
    mode        = request.form.get("mode", "").strip()
    car_raw     = request.form.get("car", "").strip()
    notes       = request.form.get("notes", "").strip()
    round_trip  = request.form.get("round_trip", "0") == "1"

    if not (date and start and end and mode):
        return redirect(url_for("index", error="Date, start, end, and mode are required."))

    if mode not in MODES:
        return redirect(url_for("index", error=f"Unknown mode: {mode!r}"))

    car_name = parse_car(car_raw) if car_raw else None
    if car_raw and car_name is None:
        return redirect(url_for("index", error=f"Unknown car: {car_raw!r}. Check config.py."))

    try:
        miles = log_trip(date=date, start=start, end=end, mode=mode, car_name=car_name, notes=notes)
        if round_trip:
            log_trip(date=date, start=end, end=start, mode=mode, car_name=car_name, notes=notes)
    except ORSError as exc:
        return redirect(url_for("index", error=f"Could not resolve route: {exc}"))

    return redirect(url_for("index", logged=f"{miles:.1f}", round_trip="1" if round_trip else "0"))


@app.route("/api/autocomplete")
def api_autocomplete():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    try:
        lon = request.args.get("lon", type=float)
        lat = request.args.get("lat", type=float)
        focus = {"lon": lon, "lat": lat} if lon is not None and lat is not None else None
        return jsonify(autocomplete(q, focus=focus))
    except Exception:
        return jsonify([])


@app.route("/api/reverse-geocode")
def api_reverse_geocode():
    try:
        lon = float(request.args["lon"])
        lat = float(request.args["lat"])
    except (KeyError, ValueError):
        return jsonify({"error": "lon and lat required"}), 400
    try:
        from ors import reverse_geocode
        return jsonify({"label": reverse_geocode(lon, lat)})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/summary")
def api_summary():
    return jsonify(get_summary())


@app.route("/api/sync", methods=["POST"])
def api_sync():
    # Manual Sheets sync hook — kept for optional fallback use
    try:
        from sync_sheets import run_sync
        return jsonify(run_sync())
    except ImportError:
        return jsonify({"error": "Sheets sync not configured"}), 501


if __name__ == "__main__":
    app.run(debug=True)
