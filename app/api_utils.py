from __future__ import annotations

from typing import Optional

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from flask import current_app, request
from flask_login import current_user

from app.models import User, Location, SavedRoute


def _get_serializer() -> URLSafeTimedSerializer:
    secret = current_app.config.get("SECRET_KEY", "")
    if isinstance(secret, bytes):
        secret = secret.decode("utf-8", errors="ignore")
    return URLSafeTimedSerializer(secret, salt="api-token")


def generate_api_token(user: User) -> str:
    serializer = _get_serializer()
    return serializer.dumps({"user_id": user.id})


def verify_api_token(token: str, max_age: int) -> Optional[User]:
    serializer = _get_serializer()
    try:
        payload = serializer.loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    user_id = payload.get("user_id")
    if not user_id:
        return None
    return User.query.get(int(user_id))


def get_api_user() -> Optional[User]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        if token:
            max_age = current_app.config.get("API_TOKEN_MAX_AGE", 60 * 60 * 24 * 14)
            user = verify_api_token(token, max_age=max_age)
            if user:
                return user
    if current_user.is_authenticated:
        return current_user
    return None


def location_to_dict(location: Location) -> dict:
    return {
        "id": location.id,
        "name": location.name,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "category_id": location.category_id,
        "category_name": location.category_name,
        "address": location.address,
        "image": location.image,
        "avg_sentiment": location.avg_sentiment,
    }


def saved_route_to_dict(route: SavedRoute, include_locations: bool = True) -> dict:
    payload = {
        "id": route.id,
        "distance": route.distance,
        "satisfaction": route.satisfaction,
        "travel_mode": route.travel_mode,
        "is_public": route.is_public,
    }
    if include_locations:
        payload["locations"] = [location_to_dict(loc) for loc in route.locations]
    return payload
