document.addEventListener('DOMContentLoaded', function() {
    const map = L.map('map').setView([51.5074, -0.1278], 13);
    const resultsLayer = L.featureGroup().addTo(map);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    /**
     * Creates a custom colored icon for Leaflet maps.
     */
    function createColoredIcon(color) {
        return L.divIcon({
            className: 'custom-icon',
            html: `<div style="background-color:${color}; width:12px; height:12px; border-radius:50%;"></div>`,
            iconSize: [12, 12],
            iconAnchor: [6, 6]
        });
    }

    /**
     * Fetches and displays all initial locations.
     */
    function fetchAndDisplayAllLocations() {
        fetch('/api/locations')
            .then(res => res.json())
            .then(locations => {
                const ColoursbyCategory = { 1: 'red', 2: 'blue', 3: 'yellow', 4: 'green', 5: 'purple', 6: 'black' };
                locations.forEach(loc => {
                    const colour = ColoursbyCategory[loc.category] || 'gray';
                    L.marker([loc.latitude, loc.longitude], { icon: createColoredIcon(colour) })
                        .addTo(map)
                        .bindPopup(`<b>${loc.name}</b><br>Tiktok Satisfaction Rating: ${loc.tiktok_rating}`);
                });
            })
            .catch(err => console.error("Failed to load initial locations:", err));
    }

    /**
     * Clears all generated routes from the map.
     */
    function clearMap() {
        resultsLayer.clearLayers();
    }

    /**
     * Generates and displays optimized routes.
     */
    function generateRoute(categoryID) {
        clearMap();
        document.body.style.cursor = 'wait';

        fetch('/api/optimize_routes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ preferences: [categoryID] })
        })
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok.');
            return response.json();
        })
        .then(data => {
            let routes = data;
            if (!routes || routes.length === 0) {
                alert("No routes could be generated for this category.");
                return;
            }
            const routeColors = ['#007bff', '#28a745', '#dc3545'];
            routes.forEach((route, index) => {
                if (route.geometry) {
                    L.geoJSON(route.geometry, {
                        style: { color: routeColors[index % routeColors.length], weight: 6, opacity: 0.75 }
                    }).addTo(resultsLayer);
                }
                route.locations.forEach(loc => {
                    L.marker([loc.latitude, loc.longitude], { icon: createColoredIcon(loc.color) })
                        .bindPopup(`<b>${loc.name}</b><br>Route: ${index + 1}<br>Satisfaction: ${route.satisfaction.toFixed(2)}`)
                        .addTo(resultsLayer);
                });
            });

            if (resultsLayer.getLayers().length > 0) {
                map.fitBounds(resultsLayer.getBounds().pad(0.1));
            }
        })
        .catch(error => {
            console.error('Route Generation Error:', error);
            alert('Failed to generate routes. Check console for details.');
        })
        .finally(() => {
            document.body.style.cursor = 'default';
        });
    }

    // --- SETUP EVENT LISTENERS (THE CRITICAL FIX) ---
    const form = document.getElementById('category-form');
    if (form) {
        form.addEventListener('submit', function(event) {
            event.preventDefault(); // Prevent page reload
            const categoryID = document.getElementById('category_select').value;
            generateRoute(categoryID);
        });
    }

    const clearButton = document.getElementById('clearroute-btn');
    if (clearButton) {
        // This properly connects the button to the function
        clearButton.addEventListener('click', clearMap);
    }

    // --- INITIAL LOAD ---
    fetchAndDisplayAllLocations();
});
