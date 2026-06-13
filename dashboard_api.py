"""
dashboard_api.py — GRID CONTROL API entrypoint.

Thin: pulls the Flask `app` + helpers from core, registers the route
blueprints (routes/*.py), and launches. gunicorn target: dashboard_api:app.
"""
from core import *  # noqa: F401,F403

from routes.brands import bp as brands_bp
from routes.agents import bp as agents_bp
from routes.content import bp as content_bp
from routes.brain import bp as brain_bp
from routes.billing import bp as billing_bp
from routes.connections import bp as connections_bp
from routes.system import bp as system_bp

for _bp in (brands_bp, agents_bp, content_bp, brain_bp, billing_bp, connections_bp, system_bp):
    app.register_blueprint(_bp)


if __name__ == "__main__":
    print("GRID CONTROL Flask API — port 5001")
    app.run(host="0.0.0.0", port=5001, debug=False)
