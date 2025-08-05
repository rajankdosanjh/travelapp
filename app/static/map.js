let userSelectedLocations = [];
let allLocations = {};
let routeIncludedLocations = new Set();

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

//Updates route included locations
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

// Checks if a location is in any route
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

    // Add/remove route button
    const routeButton = document.createElement('button');
    routeButton.className = "btn btn-info";
    routeButton.textContent = isSelected ? 'Remove From Route': 'Add to Route';

    routeButton.addEventListener('click', async () => {
    const categoryID = document.getElementById('category_select').value;
    const wasSelected = userSelectedLocations.includes(loc.id) || isLocationInRoute(loc.id);


    // Update selections
    if (wasSelected) {
        userSelectedLocations = userSelectedLocations.filter(id => id !== loc.id);
        routeIncludedLocations.delete(loc.id);
        updateSelectedLocationsList();
        updateRouteIncludedLocations();
        container.appendChild(routeButton);
    } else {
        if (!userSelectedLocations.includes(loc.id)) {
            userSelectedLocations.push(loc.id);
            updateSelectedLocationsList();
            updateRouteIncludedLocations();
            container.appendChild(routeButton);
        }
    }

    // Close popup to prevent visual glitches
    marker.closePopup();

    // Force route regeneration
    await generateRoute(categoryID);

    // Reopen popup with updated state
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
            routesContainer.innerHTML = '';
        }
        userSelectedLocations = [];
        routeIncludedLocations.clear();
        updateSelectedLocationsList();
    }

    function generateRoute(categoryID) {
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


            updateRouteIncludedLocations(routes);

            if (!routes || routes.length === 0) {
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
                    const marker = L.marker([loc.latitude, loc.longitude], { icon: createColoredIcon(loc.color) })
                        .addTo(resultsLayer);
                    marker.bindPopup(() => createPopUps(allLocations[loc.id], marker));
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