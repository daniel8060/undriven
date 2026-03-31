from flask import Flask, jsonify, render_template
import config
from db import init_db, get_summary
from sync import run_sync

app = Flask(__name__)

init_db()


@app.route("/")
def index():
    sync = run_sync()
    summary = get_summary()
    return render_template("index.html", summary=summary, sync=sync, config_cars=config.CARS)


@app.route("/api/summary")
def api_summary():
    return jsonify(get_summary())


@app.route("/api/sync", methods=["POST"])
def api_sync():
    return jsonify(run_sync())


if __name__ == "__main__":
    app.run(debug=True)
