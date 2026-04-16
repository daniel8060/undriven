import os

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from flask_migrate import Migrate

import config
from models import SavedCar, User, db

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

    login_manager = LoginManager(app)
    login_manager.login_view = "login"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    import subprocess
    try:
        rev = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                      cwd=basedir, text=True).strip()
    except Exception:
        rev = "0"
    app.config["GIT_REV"] = rev

    _register_routes(app)
    _register_cli(app)
    return app


def _register_cli(app):
    import click

    @app.cli.command("create-user")
    @click.argument("username")
    @click.password_option(prompt="Password", confirmation_prompt=True)
    def create_user(username, password):
        """Create a new user account."""
        with app.app_context():
            if User.query.filter_by(username=username).first():
                click.echo(f"Error: username '{username}' already exists.", err=True)
                raise SystemExit(1)
            u = User(username=username)
            u.set_password(password)
            db.session.add(u)
            db.session.commit()
            click.echo(f"Created user '{username}' (id={u.id}).")

    @app.cli.command("seed-cars")
    @click.argument("username")
    def seed_cars(username):
        """Seed saved cars from config.CARS for an existing user."""
        with app.app_context():
            user = User.query.filter_by(username=username).first()
            if not user:
                click.echo(f"Error: user '{username}' not found.", err=True)
                raise SystemExit(1)
            added = 0
            for i, (name, spec) in enumerate(config.CARS.items()):
                if SavedCar.query.filter_by(user_id=user.id, name=name).first():
                    click.echo(f"  skip '{name}' (already exists)")
                    continue
                car = SavedCar(
                    user_id=user.id,
                    name=name,
                    mpg=spec["mpg"],
                    fuel_type=spec.get("fuel_type", "gasoline"),
                    is_default=(i == 0 and not SavedCar.query.filter_by(user_id=user.id, is_default=True).first()),
                    sort_order=SavedCar.query.filter_by(user_id=user.id).count(),
                )
                db.session.add(car)
                added += 1
                click.echo(f"  added '{name}' ({spec['mpg']} mpg, {spec.get('fuel_type','gasoline')})"
                           + (" [default]" if car.is_default else ""))
            db.session.commit()
            click.echo(f"Done. {added} car(s) added for '{username}'.")


def _user_cars_dict(user) -> dict:
    """Return {name: {mpg, fuel_type}} for the given user's saved cars."""
    return {c.name: {"mpg": c.mpg, "fuel_type": c.fuel_type} for c in user.cars}


def _register_routes(app):
    from db import delete_trip, get_all_trips, get_summary
    from gmaps import MapsError, autocomplete
    from sync import log_trip, parse_car

    # ── Auth ─────────────────────────────────────────────────────────────────

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("index"))
        error = None
        username = ""
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            next_url = request.form.get("next") or url_for("index")
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                return redirect(next_url)
            error = "Invalid username or password."
        next_url = request.args.get("next", "")
        return render_template("login.html", error=error, username=username, next=next_url)

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if current_user.is_authenticated:
            return redirect(url_for("index"))
        error = None
        username = ""
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            password2 = request.form.get("password2", "")
            if not username or not password:
                error = "Username and password are required."
            elif password != password2:
                error = "Passwords do not match."
            elif User.query.filter_by(username=username).first():
                error = "Username already taken."
            else:
                u = User(username=username)
                u.set_password(password)
                db.session.add(u)
                db.session.commit()
                login_user(u)
                return redirect(url_for("index"))
        return render_template("signup.html", error=error, username=username)

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    # ── Main routes ───────────────────────────────────────────────────────────

    @app.route("/")
    @login_required
    def index():
        summary    = get_summary()
        logged     = request.args.get("logged")
        error      = request.args.get("error")
        round_trip = request.args.get("round_trip")
        return render_template(
            "index.html",
            summary=summary,
            user_cars=current_user.cars,
            modes=MODES,
            logged=logged,
            error=error,
            round_trip=round_trip,
            rev=app.config["GIT_REV"],
        )

    @app.route("/log", methods=["POST"])
    @login_required
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

        cars = _user_cars_dict(current_user)
        car_name = parse_car(car_raw, cars) if car_raw else None
        if car_raw and car_name is None:
            return redirect(url_for("index", error=f"Unknown car: {car_raw!r}"))

        try:
            miles = log_trip(date=date, start=start, end=end, mode=mode,
                             car_name=car_name, notes=notes, cars=cars)
            if round_trip:
                log_trip(date=date, start=end, end=start, mode=mode,
                         car_name=car_name, notes=notes, cars=cars)
        except MapsError as exc:
            return redirect(url_for("index", error=f"Could not resolve route: {exc}"))

        return redirect(url_for("index", logged=f"{miles:.1f}", round_trip="1" if round_trip else "0"))

    @app.route("/cars")
    @login_required
    def cars():
        return render_template("cars.html", user_cars=current_user.cars,
                               rev=app.config["GIT_REV"])

    @app.route("/trips")
    @login_required
    def trips():
        all_trips = get_all_trips()
        deleted   = request.args.get("deleted")
        return render_template("trips.html", trips=all_trips, deleted=deleted)

    @app.route("/trips/<int:trip_id>/delete", methods=["POST"])
    @login_required
    def trip_delete(trip_id):
        delete_trip(trip_id)
        return redirect(url_for("trips", deleted="1"))

    # ── Cars API ──────────────────────────────────────────────────────────────

    @app.route("/api/cars", methods=["GET"])
    @login_required
    def api_cars_list():
        return jsonify([
            {"id": c.id, "name": c.name, "mpg": c.mpg,
             "fuel_type": c.fuel_type, "is_default": c.is_default}
            for c in current_user.cars
        ])

    @app.route("/api/cars", methods=["POST"])
    @login_required
    def api_cars_create():
        data = request.get_json(force=True)
        name      = (data.get("name") or "").strip()
        mpg       = data.get("mpg")
        fuel_type = (data.get("fuel_type") or "gasoline").strip()
        if not name or mpg is None:
            return jsonify({"error": "name and mpg are required"}), 400
        try:
            mpg = float(mpg)
        except (TypeError, ValueError):
            return jsonify({"error": "mpg must be a number"}), 400
        if SavedCar.query.filter_by(user_id=current_user.id, name=name).first():
            return jsonify({"error": f"car '{name}' already exists"}), 409

        no_default_yet = not SavedCar.query.filter_by(user_id=current_user.id, is_default=True).first()
        next_order = SavedCar.query.filter_by(user_id=current_user.id).count()
        car = SavedCar(user_id=current_user.id, name=name, mpg=mpg,
                       fuel_type=fuel_type, is_default=no_default_yet, sort_order=next_order)
        db.session.add(car)
        db.session.commit()
        return jsonify({"id": car.id, "name": car.name, "mpg": car.mpg,
                        "fuel_type": car.fuel_type, "is_default": car.is_default}), 201

    @app.route("/api/cars/<int:car_id>", methods=["PATCH"])
    @login_required
    def api_cars_update(car_id):
        car = SavedCar.query.filter_by(id=car_id, user_id=current_user.id).first_or_404()
        data = request.get_json(force=True)
        if "name" in data:
            car.name = data["name"].strip()
        if "mpg" in data:
            car.mpg = float(data["mpg"])
        if "fuel_type" in data:
            car.fuel_type = data["fuel_type"].strip()
        db.session.commit()
        return jsonify({"id": car.id, "name": car.name, "mpg": car.mpg,
                        "fuel_type": car.fuel_type, "is_default": car.is_default})

    @app.route("/api/cars/<int:car_id>", methods=["DELETE"])
    @login_required
    def api_cars_delete(car_id):
        car = SavedCar.query.filter_by(id=car_id, user_id=current_user.id).first_or_404()
        was_default = car.is_default
        db.session.delete(car)
        db.session.flush()
        if was_default:
            next_car = SavedCar.query.filter_by(user_id=current_user.id).first()
            if next_car:
                next_car.is_default = True
        db.session.commit()
        return "", 204

    @app.route("/api/cars/reorder", methods=["POST"])
    @login_required
    def api_cars_reorder():
        ids = request.get_json(force=True).get("ids", [])
        cars_by_id = {c.id: c for c in current_user.cars}
        for order, car_id in enumerate(ids):
            if car_id in cars_by_id:
                cars_by_id[car_id].sort_order = order
        db.session.commit()
        return "", 204

    @app.route("/api/cars/<int:car_id>/set-default", methods=["POST"])
    @login_required
    def api_cars_set_default(car_id):
        car = SavedCar.query.filter_by(id=car_id, user_id=current_user.id).first_or_404()
        SavedCar.query.filter_by(user_id=current_user.id, is_default=True).update({"is_default": False})
        car.is_default = True
        db.session.commit()
        return jsonify({"id": car.id, "is_default": True})

    # ── Other API ─────────────────────────────────────────────────────────────

    @app.route("/api/autocomplete")
    @login_required
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
    @login_required
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
    @login_required
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
    @login_required
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
    @login_required
    def api_summary():
        return jsonify(get_summary())

    @app.route("/api/sync", methods=["POST"])
    @login_required
    def api_sync():
        try:
            from sync_sheets import run_sync
            return jsonify(run_sync())
        except ImportError:
            return jsonify({"error": "Sheets sync not configured"}), 501


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
