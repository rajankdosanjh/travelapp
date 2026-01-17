from __future__ import annotations

from flask import Blueprint, jsonify, request
import sqlalchemy as sa

from app import db
from app.models import Location, SavedRoute, User
from app.nsga_core import get_optimized_routes, recalculate_route_geometry
from app.api_utils import (
    generate_api_token,
    get_api_user,
    location_to_dict,
    saved_route_to_dict,
)


api_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


@api_bp.get("/health")
def api_health():
    return jsonify({"status": "ok"})


@api_bp.post("/auth/register")
def api_register():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not name or not username or not password:
        return jsonify({"error": "name, username, and password are required"}), 400

    existing = db.session.scalar(sa.select(User).where(User.username == username))
    if existing:
        return jsonify({"error": "username already taken"}), 409

    user = User(name=name, username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = generate_api_token(user)
    return jsonify({"token": token, "user": {"id": user.id, "name": user.name, "username": user.username}})


@api_bp.post("/auth/login")
def api_login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    user = db.session.scalar(sa.select(User).where(User.username == username))
    if not user or not user.check_password(password):
        return jsonify({"error": "invalid credentials"}), 401

    token = generate_api_token(user)
    return jsonify({"token": token, "user": {"id": user.id, "name": user.name, "username": user.username}})


@api_bp.post("/auth/logout")
def api_logout():
    return jsonify({"success": True})


@api_bp.get("/locations")
def api_locations():
    locations = db.session.scalars(sa.select(Location).order_by(Location.name)).all()
    return jsonify({"locations": [location_to_dict(loc) for loc in locations]})


@api_bp.get("/locations/<int:location_id>")
def api_location_detail(location_id: int):
    location = db.session.get(Location, location_id)
    if not location:
        return jsonify({"error": "location not found"}), 404
    return jsonify({"location": location_to_dict(location)})


@api_bp.post("/routes/optimize")
def api_optimize_routes():
    data = request.get_json() or {}
    if "preferences" not in data:
        return jsonify({"error": "preferences not provided"}), 400

    user_preferences = data.get("preferences", [])
    required_stops = data.get("required_stops", [])
    travel_mode = data.get("travel_mode", "walking")

    try:
        optimized_routes = get_optimized_routes(user_preferences, required_stops, travel_mode)
    except Exception as exc:
        return jsonify({"error": "route optimization failed", "detail": str(exc)}), 500

    return jsonify({"routes": optimized_routes})


@api_bp.post("/routes/recalculate")
def api_recalculate_route():
    data = request.get_json() or {}
    if "location_ids" not in data:
        return jsonify({"error": "location_ids not provided"}), 400

    location_ids = data.get("location_ids") or []
    travel_mode = data.get("travel_mode", "walking")

    try:
        route_details = recalculate_route_geometry(location_ids, travel_mode)
    except Exception as exc:
        return jsonify({"error": "route recalculation failed", "detail": str(exc)}), 500

    return jsonify(route_details)


@api_bp.post("/routes/save")
def api_save_route():
    user = get_api_user()
    if not user:
        return jsonify({"error": "To save a route, sign up or login!"}), 401

    route_to_save = request.get_json() or {}
    if not route_to_save:
        return jsonify({"error": "No route data provided"}), 400

    new_route = SavedRoute(
        distance=route_to_save.get("distance", 0),
        satisfaction=route_to_save.get("satisfaction", 0),
        travel_mode=route_to_save.get("travel_mode", "walking"),
        user=user,
    )

    location_ids = [loc.get("id") for loc in route_to_save.get("locations", []) if loc.get("id")]
    if not location_ids:
        return jsonify({"error": "Route has no locations"}), 400

    locations = db.session.scalars(sa.select(Location).where(Location.id.in_(location_ids))).all()
    new_route.locations.extend(locations)

    db.session.add(new_route)
    db.session.commit()

    return jsonify({"success": True, "route": saved_route_to_dict(new_route)})


@api_bp.get("/routes")
def api_list_routes():
    user = get_api_user()
    if not user:
        return jsonify({"error": "authentication required"}), 401

    routes = db.session.scalars(
        sa.select(SavedRoute).where(SavedRoute.user == user).order_by(SavedRoute.id.desc())
    ).all()
    return jsonify({"routes": [saved_route_to_dict(route) for route in routes]})


@api_bp.get("/routes/<int:route_id>")
def api_route_detail(route_id: int):
    user = get_api_user()
    if not user:
        return jsonify({"error": "authentication required"}), 401

    route = db.session.scalar(sa.select(SavedRoute).where(SavedRoute.id == route_id, SavedRoute.user == user))
    if not route:
        return jsonify({"error": "route not found"}), 404

    return jsonify({"route": saved_route_to_dict(route)})
