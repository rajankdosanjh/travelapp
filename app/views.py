from flask import render_template, jsonify, request
from app import app
from app.forms import RouteCategoryForm
from app.models import Location
from app.nsga_core import get_optimized_routes


@app.route("/", methods=["GET", "POST"])
def home():
    return render_template('home.html', title="Home")

@app.route("/locations")
def locations():
    form = RouteCategoryForm()
    return render_template("locations.html", title="Locations Map", form=form)

@app.route('/api/locations')
def show_locations():
    location = Location.query.all()
    data = []
    for loc in location:
        location_data = {
            'id': loc.id,
            'name': loc.name,
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'category': loc.category,
            'tiktok_rating': loc.tiktok_rating
        }
        data.append(location_data)

    return jsonify(data)


@app.route('/api/optimize_routes', methods=['POST'])
def optimize_routes_endpoint():
    """Receives user preferences, runs the NSGA-II algorithm, and returns the results."""
    try:
        data = request.get_json()
        if not data or 'preferences' not in data:
            return jsonify({"error": "User preferences not provided."}), 400

        user_prefs = data.get('preferences', [])

        optimized_routes = get_optimized_routes(user_prefs)
        return jsonify(optimized_routes)
    except Exception as e:
        print(f"Error during optimization: {e}")
        return jsonify({"error": "An error occurred during route optimization."}), 500

# Error handlers
# See: https://en.wikipedia.org/wiki/List_of_HTTP_status_codes

# Error handler for 403 Forbidden
@app.errorhandler(403)
def error_403(error):
    return render_template('errors/403.html', title='Error'), 403

# Handler for 404 Not Found
@app.errorhandler(404)
def error_404(error):
    return render_template('errors/404.html', title='Error'), 404

@app.errorhandler(413)
def error_413(error):
    return render_template('errors/413.html', title='Error'), 413

# 500 Internal Server Error
@app.errorhandler(500)
def error_500(error):
    return render_template('errors/500.html', title='Error'), 500