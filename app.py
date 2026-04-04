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

        try:
            miles = log_trip(date=date, start=start, end=end, mode=mode, car_name=car_name, notes=notes)
            if round_trip:
                log_trip(date=date, start=end, end=start, mode=mode, car_name=car_name, notes=notes)
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
                json={
                    "coordinates": [list(start_coord), list(end_coord)],
                    "geometry": True,
                    "geometry_format": "geojson",
                },
                timeout=15,
            )
            data = resp.json()
            if resp.status_code != 200:
                return jsonify({"error": data}), 502
            summary  = data["routes"][0]["summary"]
            coords   = data["routes"][0]["geometry"]["coordinates"]  # [[lon,lat],...]
            miles    = summary["distance"] / 1609.344
            # Sample ~10 evenly-spaced waypoints and build a Google Maps directions URL
            # so you can see exactly what road ORS chose vs what Maps would pick.
            sample = coords[::max(1, len(coords) // 10)]
            waypoints = "|".join(f"{c[1]},{c[0]}" for c in sample[1:-1])
            route_url = (
                "https://www.google.com/maps/dir/?api=1"
                f"&origin={start_coord[1]},{start_coord[0]}"
                f"&destination={end_coord[1]},{end_coord[0]}"
                + (f"&waypoints={waypoints}" if waypoints else "")
            )
            return jsonify({
                "start":        {"query": start, "lon": start_coord[0], "lat": start_coord[1]},
                "end":          {"query": end,   "lon": end_coord[0],   "lat": end_coord[1]},
                "miles":        round(miles, 2),
                "duration_min": round(summary["duration"] / 60, 1),
                "waypoints":    len(coords),
                "route_url":    route_url,
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
