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

    import subprocess
    try:
        rev = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                      cwd=basedir, text=True).strip()
    except Exception:
        rev = "0"
    app.config["GIT_REV"] = rev

    _register_routes(app)
    return app


def _register_routes(app):
    from db import delete_trip, get_all_trips, get_summary
    from gmaps import MapsError, autocomplete
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
            rev=app.config["GIT_REV"],
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
            miles = log_trip(date=date, start=start, end=end, mode=mode,
                             car_name=car_name, notes=notes)
            if round_trip:
                log_trip(date=date, start=end, end=start, mode=mode,
                         car_name=car_name, notes=notes)
        except MapsError as exc:
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
            from gmaps import reverse_geocode
            return jsonify({"label": reverse_geocode(lon, lat)})
        except Exception as e:
            return jsonify({"error": str(e)}), 502

    @app.route("/api/geocode")
    def api_geocode():
        """Diagnostic: show what coordinates Google resolves for a given address string."""
        q = request.args.get("q", "").strip()
        if not q:
            return jsonify({"error": "q param required"}), 400
        try:
            from gmaps import geocode
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
        """Diagnostic: show the Google route between two addresses."""
        import requests as _requests
        start = request.args.get("start", "").strip()
        end   = request.args.get("end",   "").strip()
        if not start or not end:
            return jsonify({"error": "start and end params required"}), 400
        try:
            resp = _requests.post(
                "https://routes.googleapis.com/directions/v2:computeRoutes",
                headers={
                    "X-Goog-Api-Key": config.GOOGLE_MAPS_API_KEY,
                    "X-Goog-FieldMask": "routes.distanceMeters,routes.duration,routes.legs.steps.navigationInstruction,routes.legs.steps.distanceMeters",
                    "Content-Type": "application/json",
                },
                json={
                    "origin":      {"address": start},
                    "destination": {"address": end},
                    "travelMode":  "DRIVE",
                },
                timeout=15,
            )
            data = resp.json()
            if "error" in data:
                return jsonify({"error": data["error"]}), 502
            route = data["routes"][0]
            miles = route["distanceMeters"] / 1609.344
            duration_s = int(route["duration"].rstrip("s"))
            steps = [
                {
                    "instruction": s.get("navigationInstruction", {}).get("instructions", ""),
                    "distance_mi": round(s.get("distanceMeters", 0) / 1609.344, 2),
                }
                for s in route.get("legs", [{}])[0].get("steps", [])
            ]
            return jsonify({
                "start":        {"query": start},
                "end":          {"query": end},
                "miles":        round(miles, 2),
                "duration_min": round(duration_s / 60, 1),
                "steps":        steps,
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
