import os

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_migrate import Migrate

import config
from models import db

MODES = ["bike", "walk", "train", "bus", "scooter", "other"]


def create_app(test_config=None):
    app = Flask(__name__)

    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(basedir, 'trips.db')}",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    Migrate(app, db)

    with app.app_context():
        db.create_all()

    _register_routes(app)
    return app


def _register_routes(app):
    from db import delete_trip, get_all_trips, get_summary
    from ors import ORSError, autocomplete
    from sync import log_trip, parse_car

    @app.route("/")
    def index():
        summary    = get_summary()
        logged     = request.args.get("logged")
        error      = request.args.get("error")
        round_trip = request.args.get("round_trip")
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
        date       = request.form.get("date",       "").strip()
        start      = request.form.get("start",      "").strip()
        end        = request.form.get("end",         "").strip()
        mode       = request.form.get("mode",        "").strip()
        car_raw    = request.form.get("car",         "").strip()
        notes      = request.form.get("notes",       "").strip()
        round_trip = request.form.get("round_trip", "0") == "1"

        if not (date and start and end and mode):
            return redirect(url_for("index", error="Date, start, end, and mode are required."))
        if mode not in MODES:
            return redirect(url_for("index", error=f"Unknown mode: {mode!r}"))

        car_name = parse_car(car_raw) if car_raw else None
        if car_raw and car_name is None:
            return redirect(url_for("index", error=f"Unknown car: {car_raw!r}. Check config.py."))

        def _parse_coord(lon_str, lat_str):
            try:
                return (float(lon_str), float(lat_str))
            except (TypeError, ValueError):
                return None

        start_coord = _parse_coord(
            request.form.get("start_lon", ""), request.form.get("start_lat", ""))
        end_coord   = _parse_coord(
            request.form.get("end_lon",   ""), request.form.get("end_lat",   ""))

        try:
            import time
            _t0 = time.perf_counter()
            coord_src = "autocomplete" if start_coord and end_coord else "geocode"
            print(f"[perf] leg1 start ({coord_src}) sc={start_coord} ec={end_coord}", flush=True)
            miles = log_trip(date=date, start=start, end=end, mode=mode,
                             car_name=car_name, notes=notes,
                             start_coord=start_coord, end_coord=end_coord)
            _t1 = time.perf_counter()
            print(f"[perf] leg1 done: {_t1-_t0:.3f}s", flush=True)
            if round_trip:
                print(f"[perf] leg2 start (swapped) sc={end_coord} ec={start_coord}", flush=True)
                log_trip(date=date, start=end, end=start, mode=mode,
                         car_name=car_name, notes=notes,
                         start_coord=end_coord, end_coord=start_coord)
                print(f"[perf] leg2 done: {time.perf_counter()-_t1:.3f}s", flush=True)
        except ORSError as exc:
            return redirect(url_for("index", error=f"Could not resolve route: {exc}"))

        return redirect(url_for("index", logged=f"{miles:.1f}", round_trip="1" if round_trip else "0"))

    @app.route("/trips")
    def trips():
        all_trips = get_all_trips()
        deleted   = request.args.get("deleted")
        return render_template("trips.html", trips=all_trips, deleted=deleted)

    @app.route("/trips/<int:trip_id>/delete", methods=["POST"])
    def trip_delete(trip_id):
        delete_trip(trip_id)
        return redirect(url_for("trips", deleted="1"))

    # ── API ──────────────────────────────────────────────────────────────────

    @app.route("/api/autocomplete")
    def api_autocomplete():
        q = request.args.get("q", "").strip()
        if len(q) < 2:
            return jsonify([])
        try:
            lon   = request.args.get("lon", type=float)
            lat   = request.args.get("lat", type=float)
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

    @app.route("/api/geocode")
    def api_geocode():
        """Diagnostic: show what coordinates ORS resolves for a given address string."""
        q = request.args.get("q", "").strip()
        if not q:
            return jsonify({"error": "q param required"}), 400
        try:
            from ors import geocode
            lon, lat = geocode(q)
            return jsonify({
                "query": q,
                "lon": lon,
                "lat": lat,
                "maps_url": f"https://www.google.com/maps?q={lat},{lon}",
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 502

    @app.route("/api/route-debug")
    def api_route_debug():
        """Diagnostic: show the ORS route between two addresses with a Google Maps link."""
        import requests as _requests
        start = request.args.get("start", "").strip()
        end   = request.args.get("end",   "").strip()
        if not start or not end:
            return jsonify({"error": "start and end params required"}), 400
        try:
            from ors import geocode, BASE_URL, _headers, ORSError
            start_coord = geocode(start)
            end_coord   = geocode(end)
            resp = _requests.post(
                f"{BASE_URL}/v2/directions/driving-car",
                headers={**_headers(), "Content-Type": "application/json"},
                params={"api_key": config.ORS_API_KEY},
                json={"coordinates": [list(start_coord), list(end_coord)]},
                timeout=15,
            )
            data = resp.json()
            if resp.status_code != 200:
                return jsonify({"error": data}), 502
            summary = data["routes"][0]["summary"]
            steps   = data["routes"][0]["segments"][0]["steps"]
            miles   = summary["distance"] / 1609.344
            route_steps = [
                {
                    "instruction": s.get("instruction", ""),
                    "name":        s.get("name", ""),
                    "distance_mi": round(s["distance"] / 1609.344, 2),
                }
                for s in steps
            ]
            return jsonify({
                "start":        {"query": start, "lon": start_coord[0], "lat": start_coord[1]},
                "end":          {"query": end,   "lon": end_coord[0],   "lat": end_coord[1]},
                "miles":        round(miles, 2),
                "duration_min": round(summary["duration"] / 60, 1),
                "steps":        route_steps,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 502

    @app.route("/api/summary")
    def api_summary():
        return jsonify(get_summary())

    @app.route("/api/sync", methods=["POST"])
    def api_sync():
        try:
            from sync_sheets import run_sync
            return jsonify(run_sync())
        except ImportError:
            return jsonify({"error": "Sheets sync not configured"}), 501


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
