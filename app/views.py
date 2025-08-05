from flask import render_template, jsonify, request, session, redirect, url_for
from app import app, db
from app.forms import RouteCategoryForm
from app.models import Location, Review
from app.nsga_core import get_optimized_routes, recalculate_route_geometry


@app.route("/", methods=["GET", "POST"])
def home():
    return render_template('home.html', title="Home")


@app.route("/locations")
def locations():
    form = RouteCategoryForm()
    return render_template("locations.html", title="Locations Map", form=form)


@app.route('/api/locations')
def show_locations():
    locations = Location.query.all()
    data = []
    for loc in locations:
        location_data = {
            'id': loc.id,
            'name': loc.name,
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'category_id': loc.category_id,
            'rating': loc.rating,
            'reviews': [review.text for review in loc.reviews]
        }
        data.append(location_data)
    return jsonify(data)


@app.route('/location/<int:location_id>/reviews')
def location_reviews(location_id):
    location = db.get_or_404(Location, location_id)
    return render_template('reviews.html', title=f"Reviews for {location.name}", location=location,
                           reviews=location.reviews)


@app.route('/api/optimize_routes', methods=['POST'])
def optimize_routes_endpoint():
    try:
        data = request.get_json()
        if not data or 'preferences' not in data:
            return jsonify({"error": "User preferences not provided."}), 400

        user_preferences = data.get('preferences', [])
        required_stops = data.get('required_stops', [])
        travel_mode = data.get('travel_mode', 'walking')

        print(f"--- Travel mode received: {travel_mode} ---")
        optimized_routes = get_optimized_routes(user_preferences, required_stops, travel_mode)

        return jsonify(optimized_routes)
    except Exception as e:
        print(f"Error during optimization: {e}")
        return jsonify({"error": "An error occurred during route optimization."}), 500


@app.route('/save_route', methods=['POST'])
def save_route():
    route_to_save = request.get_json()
    if not route_to_save:
        return jsonify({"error": "No route data provided."}), 400

    if 'saved_routes' not in session:
        session['saved_routes'] = []

    saved_routes = session['saved_routes']

    # To prevent duplicates, check if a route with the same ID is already saved
    if not any(r.get('id') == route_to_save.get('id') for r in saved_routes):
        # To keep the session small, save a version without the geometry
        route_copy = route_to_save.copy()
        route_copy.pop('geometry', None)
        saved_routes.append(route_copy)
        session['saved_routes'] = saved_routes

    return jsonify({"success": True, "message": "Route saved successfully."})


@app.route('/saved_routes')
def saved_routes():
    routes = session.get('saved_routes', [])
    return render_template('saved_routes.html', title="Saved Routes", routes=routes)


@app.route('/api/recalculate_route', methods=['POST'])  # Recalculates routes when mode of transport changes
def recalculate_route_endpoint():
    try:
        data = request.get_json()
        location_ids = data.get('location_ids', [])
        travel_mode = data.get('travel_mode', 'walking')

        if not location_ids:
            return jsonify({"error": "Location IDs not provided."}), 400

        new_route_details = recalculate_route_geometry(location_ids, travel_mode)

        if not new_route_details:
            return jsonify({"error": "Could not recalculate route."}), 500

        return jsonify(new_route_details)
    except Exception as e:
        print(f"Error during route recalculation: {e}")
        return jsonify({"error": "An error occurred during route recalculation."}), 500

@app.route('/delete_route/<int:route_id>', methods=['POST'])
def delete_route(route_id):
    if 'saved_routes' in session:
        saved_routes = session['saved_routes']
        saved_routes = [route for route in saved_routes if route.get('id') != route_id]
        session['saved_routes'] = saved_routes
    return redirect(url_for('saved_routes'))

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