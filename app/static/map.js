document.addEventListener('DOMContentLoaded', function() {      //listener function - waits for all other code to run before map is called
    const map = L.map('map').setView([51.5074, -0.1278], 13);
    const resultsLayer = L.featureGroup().addTo(map);
    const routesContainer = document.getElementById('routes-container');

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    function createColouredIcon(colour) {
        return L.divIcon({
            className: 'custom-icon',
            html: `<div style="background-color:${colour}; width:12px; height:12px; border-radius:50%;"></div>`,
            iconSize: [12, 12],
            iconAnchor: [6, 6]
        });
    }

    function fetchAndDisplayAllLocations() {
        fetch('/api/locations')
            .then(res => res.json())
            .then(locations => {
                const ColoursbyCategory = { 1: 'red', 2: 'blue', 3: 'yellow', 4: 'green', 5: 'purple', 6: 'black' };
                locations.forEach(loc => {
                    const colour = ColoursbyCategory[loc.category_id] || 'gray';
                    L.marker([loc.latitude, loc.longitude], { icon: createColouredIcon(colour) })
                        .addTo(map)
                        .bindPopup(`<b>${loc.name}</b>}`);  //<br>Rating: ${loc.rating
                });
            })
            .catch(err => console.error("Failed to load initial locations:", err));
    }

    function clearMap() {   //Clears the route details from the page
        resultsLayer.clearLayers();
        if (routesContainer) {
            routesContainer.innerHTML = '';
        }
    }

    function generateRoute(categoryID) {
        clearMap();
        document.body.style.cursor = 'wait';

        fetch('/api/optimize_routes', {     //API call to Flask server
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
            if (routesContainer) {
                routesContainer.innerHTML = '';
            }

            if (!routes || routes.length === 0) {
                alert("No routes could be generated for this category.");
                return;
            }
            const routeColours = ['#007bff', '#28a745', '#dc3545'];
            routes.forEach((route, index) => {  // Draws route geometry on the map
                if (route.geometry) {
                    L.geoJSON(route.geometry, {
                        style: { color: routeColours[index % routeColours.length], weight: 6, opacity: 0.75 }
                    }).addTo(resultsLayer);
                }

                route.locations.forEach(loc => {    // Adds markers for each location in the route
                    L.marker([loc.latitude, loc.longitude], { icon: createColouredIcon(loc.colour) })
                        .bindPopup(`<b>${loc.name}</b><br>Route: ${index + 1}<br>Avg. Rating: ${route.satisfaction.toFixed(2)}`)
                        .addTo(resultsLayer);
                });


                if (routesContainer) {
                    const routeDiv = document.createElement('div');
                    routeDiv.innerHTML = `
                        <h4>Route ${index + 1}</h4>
                        <p><strong>Average Rating:</strong> ${route.satisfaction.toFixed(2)}|
                         <strong>Route Distance:</strong> ${(route.distance / 1000).toFixed(2)} km</p>
                        <ul>
                            ${route.locations.map(loc => `<li>${loc.name}</li>`).join('')}
                        </ul>
                    `;
                    routesContainer.appendChild(routeDiv);
                }
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

    const form = document.getElementById('category-form');
    if (form) {
        form.addEventListener('submit', function(event) {
            event.preventDefault();
            const categoryID = document.getElementById('category_select').value;
            generateRoute(categoryID);
        });
    }

    const clearButton = document.getElementById('clearroute-btn');
    if (clearButton) {
        clearButton.addEventListener('click', clearMap);
    }

    fetchAndDisplayAllLocations();
});