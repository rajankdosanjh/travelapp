from flask import render_template, jsonify, request
from app import app
from app.models import Location

@app.route("/", methods=["GET", "POST"])
def home():
    return render_template('home.html', title="Home")

@app.route("/locations")
def locations():
        return render_template("locations.html", title="Locations Map")

@app.route('/api/locations')
def show_locations():
    location = Location.query.all()
    data = []
    for loc in location:
    # 3. Create a dictionary for the current location
        location_data = {
            'id': loc.id,
            'name': loc.name,
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'category': loc.category
        }
        data.append(location_data)

    return jsonify(data)

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