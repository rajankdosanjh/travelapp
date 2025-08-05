let userSelectedLocations = [];
let allLocations = {};
let routeIncludedLocations = new Set();
let currentTravelMode = 'walking';
let currentDisplayedRoutes = [];

function updateSelectedLocationsList() {
    const listElement = document.getElementById('selected-locations-list');
    const emptyMessage = document.getElementById('empty-selection-message');
    listElement.innerHTML = '';

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

function updateRouteIncludedLocations(routes) {
    routeIncludedLocations.clear();
    if (routes && routes.length > 0) {
        routes.forEach(route => {
            route.locations.forEach(loc => {
                routeIncludedLocations.add(loc.id);
            });
        });
    }
}

function isLocationInRoute(locId) {
    return routeIncludedLocations.has(locId);
}

function createPopUps(loc, marker) {
    const container = document.createElement('div');
    const isSelected = userSelectedLocations.includes(loc.id) || isLocationInRoute(loc.id);


    const nameElement = document.createElement('b');
    nameElement.textContent = loc.name;
    container.appendChild(nameElement);
    container.appendChild(document.createElement('br'));


    if (loc.reviews && loc.reviews.length > 0) {
        const reviewsButton = document.createElement('a');
        reviewsButton.href = `location/${loc.id}/reviews`;
        reviewsButton.className = "btn btn-info";
        reviewsButton.textContent = 'See Reviews';
        reviewsButton.style.marginRight = '5px';
        container.appendChild(reviewsButton);
    } else {
        const noReviews = document.createElement('p');
        noReviews.textContent = 'No Reviews Available';
        container.appendChild(noReviews);
    }

    const routeButton = document.createElement('button');
    routeButton.className = "btn btn-info";
    routeButton.textContent = isSelected ? 'Remove From Route': 'Add to Route';

    routeButton.addEventListener('click', async () => {
        const categoryID = document.getElementById('category_select').value;
        const wasSelected = userSelectedLocations.includes(loc.id) || isLocationInRoute(loc.id);

        if (wasSelected) {
            userSelectedLocations = userSelectedLocations.filter(id => id !== loc.id);
        } else {
            if (!userSelectedLocations.includes(loc.id)) {
                userSelectedLocations.push(loc.id);
            }
        }
        updateSelectedLocationsList();
        marker.closePopup();
        await generateRoute(categoryID); // Regenerate routes from scratch
        marker.bindPopup(() => createPopUps(loc, marker)).openPopup();
    });

    container.appendChild(routeButton);
    return container;
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
                locations.forEach(loc => {
                    allLocations[loc.id] = loc;
                });
                const ColoursbyCategory = {1: 'red', 2: 'blue', 3: 'yellow', 4: 'green', 5: 'purple', 6: 'black'};
                locations.forEach(loc => {
                    const colour = ColoursbyCategory[loc.category_id] || 'gray';
                    const marker = L.marker([loc.latitude, loc.longitude], {icon: createColoredIcon(colour)})
                        .addTo(map);

                    marker.bindPopup(() => createPopUps(loc, marker));
                });
            })
            .catch(err => console.error("Failed to load locations:", err))
    }

    function clearMap() {
        resultsLayer.clearLayers();
        if (routesContainer) {
            routesContainer.innerHTML = '<h2>Your Optimized Routes</h2>';
        }
        userSelectedLocations = [];
        routeIncludedLocations.clear();
        currentDisplayedRoutes = []; // Clear stored routes
        updateSelectedLocationsList();
    }

    //Updates the route details panel when mode of transport changes
    function updateRouteDetailsUI() {
        if (!routesContainer) return;
        routesContainer.innerHTML = '<h2>Your Optimized Routes</h2>';

        currentDisplayedRoutes.forEach((route, index) => {
            const routeDiv = document.createElement('div');
            routeDiv.innerHTML = `
                <h4>Route ${index + 1}</h4>
                <p>
                    <strong>Average Rating:</strong> ${route.satisfaction.toFixed(2)} | 
                    <strong>Total Distance:</strong> ${(route.distance / 1000).toFixed(2)} km
                </p>`;
            const ul = document.createElement('ul');
            route.locations.forEach(loc => {
                const li = document.createElement('li');
                li.textContent = `${loc.name} `;
                ul.appendChild(li);
            });
            routeDiv.appendChild(ul);

            const saveButton = document.createElement('button');
            saveButton.className = 'btn btn-success mt-2';
            saveButton.textContent = 'Save Route';
            saveButton.onclick = () => saveRoute(route.id);
            routeDiv.appendChild(saveButton);

            routesContainer.appendChild(routeDiv);
        });
    }

    function saveRoute(routeId) {
        const routeToSave = currentDisplayedRoutes.find(r => r.id === routeId);
        if (!routeToSave) {
            alert('Error: Could not find route data to save.');
            return;
        }

        fetch(`/save_route`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(routeToSave) // Sends the entire route object in the body
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Route saved!');
            } else {
                alert(`Error saving route: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while saving the route.');
        });
    }

    //Redraws routes with a new mode of transport (links to previous function)
    async function redrawRoutesWithNewMode(newMode) {
        if (currentDisplayedRoutes.length === 0) return;

        document.body.style.cursor = 'wait';
        resultsLayer.clearLayers();
        const routeColors = ['#007bff', '#28a745', '#dc3545'];

        for (let i = 0; i < currentDisplayedRoutes.length; i++) {
            const route = currentDisplayedRoutes[i];
            const location_ids = route.locations.map(loc => loc.id);

            try {
                const response = await fetch('/api/recalculate_route', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        location_ids: location_ids,
                        travel_mode: newMode
                    })
                });

                if (!response.ok) throw new Error('Recalculation failed');
                const newDetails = await response.json();

                route.distance = newDetails.distance;
                route.geometry = newDetails.geometry;

                if (route.geometry) {
                    L.geoJSON(route.geometry, {
                        style: { color: routeColors[i % routeColors.length], weight: 6, opacity: 0.75 }
                    }).addTo(resultsLayer);
                }
                route.locations.forEach(loc => {
                    const marker = L.marker([loc.latitude, loc.longitude], { icon: createColoredIcon(loc.color) })
                        .addTo(resultsLayer);
                    marker.bindPopup(() => createPopUps(allLocations[loc.id], marker));
                });
            } catch (error) {
                console.error('Error recalculating route:', error);
            }
        }

        updateRouteDetailsUI();
        document.body.style.cursor = 'default';
    }


    function generateRoute(categoryID) {
        resultsLayer.clearLayers();
        document.body.style.cursor = 'wait';

        fetch('/api/optimize_routes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                preferences: [categoryID],
                required_stops: userSelectedLocations,
                travel_mode: currentTravelMode
            })
        })
        .then(response => response.json())
        .then(data => {
            currentDisplayedRoutes = data; // Store the new routes
            updateRouteIncludedLocations(currentDisplayedRoutes);

            if (!currentDisplayedRoutes || currentDisplayedRoutes.length === 0) {
                 alert("No routes could be generated for this category.");
                return;
            }

            const routeColors = ['#007bff', '#28a745', '#dc3545'];
            currentDisplayedRoutes.forEach((route, index) => {
                if (route.geometry) {
                    L.geoJSON(route.geometry, {
                        style: { color: routeColors[index % routeColors.length], weight: 6, opacity: 0.75 }
                    }).addTo(resultsLayer);
                }
                route.locations.forEach(loc => {
                    const marker = L.marker([loc.latitude, loc.longitude], { icon: createColoredIcon(loc.color) })
                        .addTo(resultsLayer);
                    marker.bindPopup(() => createPopUps(allLocations[loc.id], marker));
                });
            });

            updateRouteDetailsUI();

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

    const travelModeSelector = document.getElementById('travel-mode-selector');
    if (travelModeSelector) {
        travelModeSelector.addEventListener('click', function(event) {
            if (event.target.classList.contains('mode-btn')) {
                travelModeSelector.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
                event.target.classList.add('active');
                currentTravelMode = event.target.dataset.mode;

                // Instead of regenerating routes which takes longer, just recalculates and redraws route when mode of transport changes
                redrawRoutesWithNewMode(currentTravelMode);
            }
        });
    }

    const clearButton = document.getElementById('clearroute-btn');
    if (clearButton) {
        clearButton.addEventListener('click', clearMap);
    }

    fetchAndDisplayAllLocations();
});