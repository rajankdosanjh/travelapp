from flask import render_template, jsonify, request, redirect, url_for, flash, abort, send_from_directory
from app import app, db
from app.forms import RouteCategoryForm, LoginForm, RegisterForm
from app.models import Location, User, SavedRoute, SavedPlace, LocationFeedback, RouteFeedback
from app.nsga_core import get_optimized_routes, recalculate_route_geometry
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlsplit, urlencode
import sqlalchemy as sa
from sqlalchemy import func
import requests
import re
import os
from uuid import uuid4
from werkzeug.utils import secure_filename
import pickle
from app.location_utils import classify_review

CATEGORY_NAMES = {
    1: 'Food and Drink',
    2: 'History',
    3: 'Shopping',
    4: 'Nature',
    5: 'Art and Culture',
    6: 'Nightlife',
}

CATEGORY_COLORS = {
    1: '#ff6b35',
    2: '#4f46e5',
    3: '#f59e0b',
    4: '#10b981',
    5: '#ec4899',
    6: '#0ea5e9',
}

ALLOWED_PHOTO_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

_sentiment_model = None

def get_sentiment_model():
    global _sentiment_model
    if _sentiment_model is None:
        with open('sentiment_classifier.pkl', 'rb') as f:
            _sentiment_model = pickle.load(f)
    return _sentiment_model

def get_sentiment_score(text):
    model = get_sentiment_model()
    score = classify_review(
        text,
        model["classifier"],
        model["vectorizer"],
        model["word_features"]
    )
    return max(-1.0, min(1.0, score))

def is_allowed_photo(filename):
    _, ext = os.path.splitext(filename)
    return ext.lower() in ALLOWED_PHOTO_EXTENSIONS

def ensure_location_address_column():
    columns = db.session.execute(sa.text("PRAGMA table_info(locations)")).fetchall()
    column_names = {col[1] for col in columns}
    if 'address' not in column_names:
        db.session.execute(sa.text("ALTER TABLE locations ADD COLUMN address VARCHAR(200)"))
        db.session.commit()


@app.route("/", methods=["GET", "POST"])
def home():
    top_locations = db.session.execute(
        sa.select(Location, func.avg(LocationFeedback.rating).label('avg_rating'), func.count(LocationFeedback.id).label('count'))
        .join(LocationFeedback, LocationFeedback.location_id == Location.id)
        .group_by(Location.id)
        .order_by(sa.desc('avg_rating'), sa.desc('count'))
        .limit(3)
    ).all()

    top_routes = db.session.execute(
        sa.select(SavedRoute, func.avg(RouteFeedback.rating).label('avg_rating'), func.count(RouteFeedback.id).label('count'))
        .join(RouteFeedback, RouteFeedback.route_id == SavedRoute.id)
        .group_by(SavedRoute.id)
        .order_by(sa.desc('avg_rating'), sa.desc('count'))
        .limit(3)
    ).all()

    recent_comments = db.session.scalars(
        sa.select(LocationFeedback).order_by(LocationFeedback.timestamp.desc()).limit(3)
    ).all()

    return render_template(
        'home.html',
        title="Home",
        top_locations=top_locations,
        top_routes=top_routes,
        recent_comments=recent_comments
    )

def build_google_maps_url(locations):
    if not locations or len(locations) < 2:
        return None
    origin = f"{locations[0].latitude},{locations[0].longitude}"
    destination = f"{locations[-1].latitude},{locations[-1].longitude}"
    waypoints = "|".join(
        f"{loc.latitude},{loc.longitude}" for loc in locations[1:-1]
    )
    params = {
        "api": 1,
        "origin": origin,
        "destination": destination
    }
    if waypoints:
        params["waypoints"] = waypoints
    return f"https://www.google.com/maps/dir/?{urlencode(params)}"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('locations'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('locations')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('locations'))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(name=form.name.data.strip(), username=form.username.data.strip())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Account created. Welcome!', 'success')
        return redirect(url_for('locations'))
    if form.errors:
        flash('Please fix the errors below and try again.', 'danger')
    return render_template('register.html', title='Register', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/locations")
def locations():
    form = RouteCategoryForm()
    return render_template("locations.html", title="Locations Map", form=form)


@app.route('/api/locations')
def show_locations():
    locations = Location.query.all()
    data = []
    for loc in locations:
        category_name = CATEGORY_NAMES.get(loc.category_id, 'Other')
        location_data = {
            'id': loc.id,
            'name': loc.name,
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'category_id': loc.category_id,
            'category_name': category_name,
            'color': CATEGORY_COLORS.get(loc.category_id, 'gray'),
            'reviews': [review.text for review in loc.reviews]
        }
        data.append(location_data)
    return jsonify(data)


def extract_coordinates(query):
    if not query:
        return None
    at_match = re.search(r'@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)', query)
    if at_match:
        return float(at_match.group(1)), float(at_match.group(2))
    q_match = re.search(r'[?&]q=([^&]+)', query)
    if q_match:
        q_value = q_match.group(1)
        coord_match = re.search(r'(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)', q_value)
        if coord_match:
            return float(coord_match.group(1)), float(coord_match.group(2))
    return None


@app.route('/api/geocode', methods=['POST'])
def geocode_location():
    data = request.get_json() or {}
    query = (data.get('query') or '').strip()
    if not query:
        return jsonify({'success': False, 'message': 'Query is required.'}), 400

    coords = extract_coordinates(query)
    headers = {'User-Agent': 'UrbanTrail/1.0 (contact: admin@urbantrail.local)'}

    try:
        if coords:
            lat, lon = coords
            response = requests.get(
                'https://nominatim.openstreetmap.org/reverse',
                params={'format': 'json', 'lat': lat, 'lon': lon},
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return jsonify({
                'success': True,
                'latitude': lat,
                'longitude': lon,
                'address': data.get('display_name')
            })

        response = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={'format': 'json', 'limit': 1, 'q': query},
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        results = response.json()
        if not results:
            return jsonify({'success': False, 'message': 'No results found.'}), 404

        result = results[0]
        return jsonify({
            'success': True,
            'latitude': float(result['lat']),
            'longitude': float(result['lon']),
            'address': result.get('display_name')
        })
    except requests.RequestException:
        return jsonify({'success': False, 'message': 'Geocoding service unavailable.'}), 502


@app.route('/api/locations/add', methods=['POST'])
def add_location():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    address = (data.get('address') or '').strip()
    category_id = data.get('category_id')
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if not name or category_id is None or latitude is None or longitude is None:
        return jsonify({'success': False, 'message': 'Name, category, latitude, and longitude are required.'}), 400

    try:
        category_id = int(category_id)
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Invalid category or coordinates.'}), 400

    if category_id not in CATEGORY_NAMES:
        return jsonify({'success': False, 'message': 'Invalid category selection.'}), 400

    existing = db.session.scalar(sa.select(Location).where(Location.name == name))
    if existing:
        return jsonify({'success': False, 'message': 'A location with this name already exists.'}), 409

    ensure_location_address_column()
    location = Location(
        name=name,
        address=address or None,
        latitude=latitude,
        longitude=longitude,
        category_id=category_id
    )
    db.session.add(location)
    db.session.commit()

    return jsonify({
        'success': True,
        'location': {
            'id': location.id,
            'name': location.name,
            'latitude': location.latitude,
            'longitude': location.longitude,
            'category_id': location.category_id,
            'category_name': CATEGORY_NAMES.get(location.category_id, 'Other'),
            'color': CATEGORY_COLORS.get(location.category_id, 'gray'),
            'reviews': []
        }
    }), 201


@app.route('/location/<int:location_id>/reviews')
def location_reviews(location_id):
    location = db.get_or_404(Location, location_id)
    feedbacks = db.session.scalars(
        sa.select(LocationFeedback)
        .where(LocationFeedback.location_id == location.id)
        .order_by(LocationFeedback.timestamp.desc())
    ).all()
    return render_template('reviews.html', title=f"Reviews for {location.name}", location=location,
                           reviews=location.reviews, avg_sentiment=location.avg_sentiment, feedbacks=feedbacks)


@app.route('/location/<int:location_id>/feedback', methods=['POST'])
@login_required
def add_location_feedback(location_id):
    location = db.get_or_404(Location, location_id)
    body = (request.form.get('body') or '').strip()

    if not body:
        flash('Please add a comment so we can analyze its sentiment.', 'danger')
        return redirect(url_for('location_reviews', location_id=location.id))

    rating = get_sentiment_score(body)

    feedback = LocationFeedback(
        location_id=location.id,
        user_id=current_user.id,
        rating=rating,
        body=body
    )
    db.session.add(feedback)
    db.session.commit()
    flash('Thanks for sharing your feedback!', 'success')
    return redirect(url_for('location_reviews', location_id=location.id))


@app.route('/api/optimize_routes', methods=['POST'])
def optimize_routes_endpoint():
    try:
        data = request.get_json()
        if not data or 'preferences' not in data:
            return jsonify({'error': 'User preferences not provided.'}), 400

        user_preferences = data.get('preferences', [])
        required_stops = data.get('required_stops', [])
        travel_mode = data.get('travel_mode', 'walking')

        print(f"--- Travel mode received: {travel_mode} ---")
        optimized_routes = get_optimized_routes(user_preferences, required_stops, travel_mode)

        return jsonify(optimized_routes)
    except Exception as e:
        print(f"Error during optimization: {e}")
        return jsonify({'error': 'An error occurred during route optimization.'}), 500


@app.route('/save_route', methods=['POST'])
def save_route():
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': 'To save a route, sign up or login!'}), 401

    route_to_save = request.get_json()
    if not route_to_save:
        return jsonify({'success': False, 'message': 'No route data provided'}), 400

    new_route = SavedRoute(
        distance=route_to_save.get('distance', 0),
        satisfaction=route_to_save.get('satisfaction', 0),
        travel_mode=route_to_save.get('travel_mode', 'walking'),
        user=current_user
    )

    # Find and associate the locations for this route
    location_ids = [loc['id'] for loc in route_to_save.get('locations', [])]
    if not location_ids:
        return jsonify({'success': False, 'message': 'Route has no locations'}), 400
    locations = db.session.scalars(sa.select(Location).where(Location.id.in_(location_ids))).all()
    new_route.locations.extend(locations)

    db.session.add(new_route)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Route saved successfully.'})


@app.route('/saved_routes')
@login_required
def saved_routes():
    user_routes = db.session.scalars(
        sa.select(SavedRoute).where(SavedRoute.user == current_user).order_by(SavedRoute.id.desc())
    ).all()
    route_ids = [route.id for route in user_routes]
    feedbacks = []
    if route_ids:
        feedbacks = db.session.scalars(
            sa.select(RouteFeedback)
            .where(RouteFeedback.route_id.in_(route_ids))
            .order_by(RouteFeedback.timestamp.desc())
        ).all()

    feedback_by_route = {}
    for feedback in feedbacks:
        feedback_by_route.setdefault(feedback.route_id, []).append(feedback)

    stats_by_route = {}
    for route_id, items in feedback_by_route.items():
        avg_rating = sum(item.rating for item in items) / len(items)
        stats_by_route[route_id] = {
            'avg_rating': avg_rating,
            'count': len(items),
            'feedbacks': items[:3]
        }

    export_urls = {}
    for route in user_routes:
        export_urls[route.id] = build_google_maps_url(route.locations)

    return render_template(
        'saved_routes.html',
        title="Saved Routes",
        routes=user_routes,
        route_feedback_stats=stats_by_route,
        route_export_urls=export_urls
    )

@app.route('/saved_routes/<int:route_id>/share', methods=['POST'])
@login_required
def toggle_route_share(route_id):
    route = db.session.scalar(
        sa.select(SavedRoute).where(SavedRoute.id == route_id, SavedRoute.user == current_user)
    )
    if not route:
        flash('Route not found.', 'danger')
        return redirect(url_for('saved_routes'))

    make_public = request.form.get('is_public') == 'on'
    route.is_public = make_public
    db.session.commit()
    if make_public:
        flash('Route shared to Community Routes.', 'success')
    else:
        flash('Route removed from Community Routes.', 'success')
    return redirect(url_for('saved_routes'))


@app.route('/community_routes')
def community_routes():
    routes = db.session.scalars(
        sa.select(SavedRoute).where(SavedRoute.is_public.is_(True)).order_by(SavedRoute.id.desc())
    ).all()

    route_ids = [route.id for route in routes]
    feedbacks = []
    if route_ids:
        feedbacks = db.session.scalars(
            sa.select(RouteFeedback)
            .where(RouteFeedback.route_id.in_(route_ids))
            .order_by(RouteFeedback.timestamp.desc())
        ).all()

    feedback_by_route = {}
    for feedback in feedbacks:
        feedback_by_route.setdefault(feedback.route_id, []).append(feedback)

    stats_by_route = {}
    for route_id, items in feedback_by_route.items():
        avg_rating = sum(item.rating for item in items) / len(items)
        stats_by_route[route_id] = {
            'avg_rating': avg_rating,
            'count': len(items),
            'feedbacks': items[:3]
        }

    export_urls = {}
    for route in routes:
        export_urls[route.id] = build_google_maps_url(route.locations)

    return render_template(
        'community_routes.html',
        title="Community Routes",
        routes=routes,
        route_feedback_stats=stats_by_route,
        route_export_urls=export_urls
    )

@app.route('/route/<int:route_id>/feedback', methods=['POST'])
@login_required
def add_route_feedback(route_id):
    route = db.session.scalar(sa.select(SavedRoute).where(SavedRoute.id == route_id))
    if not route:
        flash('Route not found.', 'danger')
        return redirect(url_for('community_routes'))

    if route.user != current_user and not route.is_public:
        flash('You can only rate public routes.', 'danger')
        return redirect(url_for('community_routes'))

    rating = request.form.get('rating', type=int)
    body = (request.form.get('body') or '').strip()

    if not rating or rating < 1 or rating > 5 or not body:
        flash('Please provide a rating (1-5) and a comment.', 'danger')
        return redirect(url_for('community_routes'))

    feedback = RouteFeedback(
        route_id=route.id,
        user_id=current_user.id,
        rating=rating,
        body=body
    )
    if route.user == current_user and not route.is_public:
        route.is_public = True
    db.session.add(feedback)
    db.session.commit()
    if route.user == current_user and route.is_public:
        flash('Thanks for rating your route! It is now visible in Community Routes.', 'success')
    else:
        flash('Thanks for rating your route!', 'success')
    if route.user == current_user:
        return redirect(url_for('saved_routes'))
    return redirect(url_for('community_routes'))


@app.route('/delete_route/<int:route_id>', methods=['POST'])
@login_required
def delete_route(route_id):
    route_to_delete = db.session.scalar(
        sa.select(SavedRoute).where(SavedRoute.id == route_id, SavedRoute.user == current_user)
    )
    if route_to_delete:
        db.session.delete(route_to_delete)
        db.session.commit()
        # Add a success message for the user
        flash('Route deleted successfully.', 'success')
    else:
        # Optional: Add a message if the route wasn't found
        flash('Could not find the route to delete.', 'danger')

    # Redirect back to the saved routes page
    return redirect(url_for('saved_routes'))


@app.route('/api/recalculate_route', methods=['POST'])  # Recalculates routes when mode of transport changes
def recalculate_route_endpoint():
    try:
        data = request.get_json()
        location_ids = data.get('location_ids', [])
        travel_mode = data.get('travel_mode', 'walking')

        if not location_ids:
            return jsonify({'error': 'Location IDs not provided.'}), 400

        new_route_details = recalculate_route_geometry(location_ids, travel_mode)

        if not new_route_details:
            return jsonify({'error': 'Could not recalculate route.'}), 400

        return jsonify(new_route_details)
    except Exception as e:
        print(f"Error during route recalculation: {e}")
        return jsonify({'error': 'An error occurred during route recalculation.'}), 500


@app.route('/save_place', methods=['POST'])
def save_place():
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': 'Login required'}), 401

    data = request.get_json()
    location_id = data.get('location_id')

    if not location_id:
        return jsonify({'success': False, 'message': 'Missing location_id'}), 400

    existing = db.session.scalar(
        sa.select(SavedPlace).where(
            SavedPlace.user_id == current_user.id,
            SavedPlace.location_id == location_id
        )
    )
    if existing:
        return jsonify({'success': True, 'message': 'Place already saved'})

    place = SavedPlace(user_id=current_user.id, location_id=location_id)
    db.session.add(place)
    db.session.commit()

    return jsonify({'success': True})

@app.route('/my_places')
@login_required
def my_places():
    places = SavedPlace.query.filter_by(user_id=current_user.id).order_by(SavedPlace.timestamp.desc()).all()
    return render_template("my_places.html", places=places)

@app.route('/my_places/photo/<int:place_id>')
@login_required
def my_place_photo(place_id):
    place = db.session.scalar(
        sa.select(SavedPlace).where(SavedPlace.id == place_id, SavedPlace.user_id == current_user.id)
    )
    if not place or not place.photo_filename:
        abort(404)
    user_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id))
    return send_from_directory(user_dir, place.photo_filename)

@app.route('/my_places/<int:place_id>/photo', methods=['POST'])
@login_required
def upload_place_photo(place_id):
    place = db.session.scalar(
        sa.select(SavedPlace).where(SavedPlace.id == place_id, SavedPlace.user_id == current_user.id)
    )
    if not place:
        abort(404)

    file = request.files.get('photo')
    if not file or file.filename == '':
        flash('Please choose an image file to upload.', 'danger')
        return redirect(url_for('my_places'))

    filename = secure_filename(file.filename)
    if not is_allowed_photo(filename):
        flash('Unsupported file type. Use JPG, PNG, GIF, or WEBP.', 'danger')
        return redirect(url_for('my_places'))

    ext = os.path.splitext(filename)[1].lower()
    new_filename = f"{uuid4().hex}{ext}"
    user_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id))
    os.makedirs(user_dir, exist_ok=True)

    if place.photo_filename:
        old_path = os.path.join(user_dir, place.photo_filename)
        if os.path.exists(old_path):
            os.remove(old_path)

    file.save(os.path.join(user_dir, new_filename))
    place.photo_filename = new_filename
    db.session.commit()
    flash('Photo uploaded.', 'success')
    return redirect(url_for('my_places'))
@app.route('/delete_place/<int:place_id>', methods=['POST'])
@login_required
def delete_place(place_id):
    place = db.session.scalar(
        sa.select(SavedPlace).where(SavedPlace.id == place_id, SavedPlace.user_id == current_user.id)
    )
    if place:
        db.session.delete(place)
        db.session.commit()
        flash('Place removed successfully.', 'success')
    else:
        flash('Could not find the saved place to remove.', 'danger')
    return redirect(url_for('my_places'))



@app.errorhandler(403)
def error_403(error):
    return render_template('errors/403.html', title='Error'), 403


@app.errorhandler(404)
def error_404(error):
    return render_template('errors/404.html', title='Error'), 404


@app.errorhandler(413)
def error_413(error):
    return render_template('errors/413.html', title='Error'), 413


@app.errorhandler(500)
def error_500(error):
    return render_template('errors/500.html', title='Error'), 500
