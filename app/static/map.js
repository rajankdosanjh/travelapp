// A global array to store user-selected location IDs
let userSelectedLocations = [];
// Global variable to hold all location data for easy lookup
let allLocations = {};

// Function to update the visible list of selected locations on the page
function updateSelectedLocationsList() {
    const listElement = document.getElementById('selected-locations-list');
    const emptyMessage = document.getElementById('empty-selection-message');
    listElement.innerHTML = ''; // Clear the list

    if (userSelectedLocations.length === 0 && emptyMessage) {
        listElement.appendChild(emptyMessage);
    } else {
        userSelectedLocations.forEach(locId => {
            const location = allLocations[locId];
            if (location) {
                const listItem = document.createElement('li');
                listItem.textContent = location.name;
                listElement.appendChild(listItem);
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const map = L.map('map').setView([51.5074, -0.1278], 13);
    const resultsLayer = L.featureGroup().addTo(map);
    const routesContainer = document.getElementById('routes-container');

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    function createColoredIcon(color) {
        return L.divIcon({
            className: 'custom-icon',
            html: `<div style="background-color:${color}; width:12px; height:12px; border-radius:50%;"></div>`,
            iconSize: [12, 12],
            iconAnchor: [6, 6]
        });
    }

    function fetchAndDisplayAllLocations() {
        fetch('/api/locations')
            .then(res => res.json())
            .then(locations => {
                locations.forEach(loc => { allLocations[loc.id] = loc; });

                const ColoursbyCategory = { 1: 'red', 2: 'blue', 3: 'yellow', 4: 'green', 5: 'purple', 6: 'black' };
                locations.forEach(loc => {
                    const colour = ColoursbyCategory[loc.category_id] || 'gray';
                    const marker = L.marker([loc.latitude, loc.longitude], { icon: createColoredIcon(colour) })
                        .addTo(map)
                        .bindPopup(() => {
                            const isSelected = userSelectedLocations.includes(loc.id);
                            const container = document.createElement('div');
                            container.innerHTML = `<b>${loc.name}</b><br>Rating: ${loc.rating}<br>`;

                            const button = document.createElement('button');
                            button.textContent = isSelected ? 'Remove from Route' : 'Add to Route';

                            button.addEventListener('click', () => {
                                if (isSelected) {
                                    userSelectedLocations = userSelectedLocations.filter(id => id !== loc.id);
                                } else {
                                    if (!userSelectedLocations.includes(loc.id)) {
                                        userSelectedLocations.push(loc.id);
                                    }
                                }
                                updateSelectedLocationsList();

                                // NEW: Automatically re-run the route generation
                                const categoryID = document.getElementById('category_select').value;
                                generateRoute(categoryID);
                            });

                            container.appendChild(button);
                            return container;
                        });
                });
            })
            .catch(err => console.error("Failed to load initial locations:", err));
    }

    function clearMap() {
        resultsLayer.clearLayers();
        if (routesContainer) {
            routesContainer.innerHTML = '';
        }
        userSelectedLocations = [];
        updateSelectedLocationsList();
    }

    function generateRoute(categoryID) {
        // We only clear the map if we are generating a new route from scratch,
        // not when updating it after adding/removing a location.
        if (userSelectedLocations.length === 0) {
            clearMap();
        } else {
            resultsLayer.clearLayers();
             if (routesContainer) {
                routesContainer.innerHTML = '';
            }
        }

        document.body.style.cursor = 'wait';

        fetch('/api/optimize_routes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                preferences: [categoryID],
                required_stops: userSelectedLocations
            })
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
                // Only show alert if the user explicitly clicked the "Generate Routes" button
                if (document.activeElement.id !== 'category-form') {
                     alert("No routes could be generated for this category.");
                }
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
                        .bindPopup(`<b>${loc.name}</b><br>Route: ${index + 1}<br>Avg. Rating: ${route.satisfaction.toFixed(2)}`)
                        .addTo(resultsLayer);
                });

                if (routesContainer) {
                    const routeDiv = document.createElement('div');
                    routeDiv.innerHTML = `
                        <h4>Route ${index + 1}</h4>
                        <p>
                            <strong>Average Rating:</strong> ${route.satisfaction.toFixed(2)} | 
                            <strong>Total Distance:</strong> ${(route.distance / 1000).toFixed(2)} km
                        </p>
                    `;

                    const ul = document.createElement('ul');
                    route.locations.forEach(loc => {
                        const li = document.createElement('li');
                        li.textContent = `${loc.name} `;

                        const removeButton = document.createElement('button');
                        removeButton.textContent = 'x';
                        removeButton.style.marginLeft = '10px';
                        removeButton.style.cursor = 'pointer';
                        removeButton.className = 'remove-loc-btn';

                        removeButton.addEventListener('click', () => {
                            const newRequiredStops = route.locations
                                .filter(l => l.id !== loc.id)
                                .map(l => l.id);

                            userSelectedLocations = newRequiredStops;
                            updateSelectedLocationsList();
                            generateRoute(categoryID);
                        });

                        li.appendChild(removeButton);
                        ul.appendChild(li);
                    });

                    routeDiv.appendChild(ul);
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