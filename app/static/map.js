let userSelectedLocations = [];
let allLocations = {};
let routeIncludedLocations = new Set(); //Creates a Set to store the IDs of all locations that are part of the currently displayed, algorithm-generated routes.
let currentTravelMode = 'walking';
let currentDisplayedRoutes = [];
const routeColorPalettes = {
    walking: ['#14b8a6', '#2dd4bf', '#0d9488'],
    driving: ['#fb7185', '#f43f5e', '#be123c'],
    cycling: ['#facc15', '#fde047', '#eab308'],
    transit: ['#38bdf8', '#0ea5e9', '#0284c7']
};
let currentRouteColors = routeColorPalettes[currentTravelMode];
const travelModeColors = {
    walking: '#14b8a6',
    driving: '#fb7185',
    cycling: '#facc15',
    transit: '#38bdf8'
};
const mapMarkersById = {};
let geocodedLocation = null;

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
                listItem.className = 'd-flex align-items-center small text-body';
                listItem.innerHTML = `
                    <i class="bi bi-dot text-primary me-1"></i>
                    <span>${location.name}</span>
                `;
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
    container.className = 'small';

    const isSelected = userSelectedLocations.includes(loc.id) || isLocationInRoute(loc.id);

    // Name
    const nameElement = document.createElement('div');
    nameElement.className = 'fw-semibold mb-1';
    nameElement.textContent = loc.name;
    container.appendChild(nameElement);

    // Category (if available)
    if (loc.category || loc.category_name) {
        const cat = document.createElement('div');
        cat.className = 'text-muted mb-2';
        cat.innerHTML = `
            <i class="bi bi-tag me-1"></i>
            ${(loc.category_name || loc.category)}
        `;
        container.appendChild(cat);
    }

    // Reviews section
    if (loc.reviews && loc.reviews.length > 0) {
        const reviewInfo = document.createElement('div');
        reviewInfo.className = 'text-muted mb-2';
        reviewInfo.innerHTML = `
            <i class="bi bi-chat-square-heart me-1"></i>
            ${loc.reviews.length} review${loc.reviews.length === 1 ? '' : 's'} available
        `;
        container.appendChild(reviewInfo);
    } else {
        const noReviews = document.createElement('div');
        noReviews.className = 'text-muted mb-2';
        noReviews.innerHTML = `
            <i class="bi bi-chat-dots me-1"></i>
            No reviews yet
        `;
        container.appendChild(noReviews);
    }

    // Button group
    const buttonRow = document.createElement('div');
    buttonRow.className = 'd-flex flex-wrap gap-2 mt-2';

    // See/Add Reviews button (always available)
    const reviewsButton = document.createElement('a');
    reviewsButton.href = `location/${loc.id}/reviews`;
    reviewsButton.className = 'btn btn-outline-primary btn-sm rounded-pill';
    if (loc.reviews && loc.reviews.length > 0) {
        reviewsButton.innerHTML = `<i class="bi bi-chat-square-text me-1"></i> See reviews`;
    } else {
        reviewsButton.innerHTML = `<i class="bi bi-chat-square-text me-1"></i> Add review`;
    }
    buttonRow.appendChild(reviewsButton);

    // Save place button
    const saveButton = document.createElement('button');
    saveButton.type = 'button';
    saveButton.className = 'btn btn-outline-secondary btn-sm rounded-pill';
    saveButton.innerHTML = `<i class="bi bi-bookmark-heart me-1"></i> Save place`;
    saveButton.addEventListener('click', () => {
        savePlace(loc.id);
    });
    buttonRow.appendChild(saveButton);

    // Add/Remove from route button
    const routeButton = document.createElement('button');
    routeButton.type = 'button';
    routeButton.className = 'btn btn-primary btn-sm rounded-pill';
    routeButton.innerHTML = isSelected
        ? `<i class="bi bi-dash-circle me-1"></i> Remove from route`
        : `<i class="bi bi-plus-circle me-1"></i> Add to route`;

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
        await generateRoute(categoryID);
        marker.bindPopup(() => createPopUps(loc, marker)).openPopup();
    });

    buttonRow.appendChild(routeButton);

    container.appendChild(buttonRow);
    return container;
}

function savePlace(locationId) {
    fetch('/save_place', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ location_id: locationId })
    })
    .then(res => {
        if (res.status === 401) {
            window.location.href = '/login';
            return Promise.reject(new Error('Login required'));
        }
        return res.json();
    })
    .then(data => {
        if (data.success) {
            // You can make this fancier with a toast later
            alert('Place saved to My Places');
        } else {
            alert(`Error saving place: ${data.message || 'Unknown error'}`);
        }
    })
    .catch(err => {
        console.error('Save place error:', err);
        alert('An error occurred while saving the place.');
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const map = L.map('map').setView([51.5074, -0.1278], 13);
    const resultsLayer = L.featureGroup().addTo(map);   //Layer that holds all the generated routes and markers, making it easy to clear them all at once.
    const routesContainer = document.getElementById('routes-container');

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    function createColoredIcon(color, iconClass) {
        return L.divIcon({
            className: 'custom-icon',
            html: `<div class="icon-pin" style="--pin-color:${color};"><i class="${iconClass}"></i></div>`,
            iconSize: [26, 26],
            iconAnchor: [13, 13]
        });
    }

    function fetchAndDisplayAllLocations() {
        fetch('/api/locations')     //API call to the /api/locations endpoint.
            .then(res => res.json())
            .then(locations => {
                const datalist = document.getElementById('location-search-list');
                const iconByCategory = {
                    1: 'bi bi-cup-hot',
                    2: 'bi bi-bank2',
                    3: 'bi bi-bag',
                    4: 'bi bi-tree',
                    5: 'bi bi-palette',
                    6: 'bi bi-moon-stars'
                };
                locations.forEach(loc => {
                    allLocations[loc.id] = loc;
                });
                const ColoursbyCategory = {
                    1: '#ff6b35',
                    2: '#4f46e5',
                    3: '#f59e0b',
                    4: '#10b981',
                    5: '#ec4899',
                    6: '#0ea5e9'
                };
                locations.forEach(loc => {
                    const colour = ColoursbyCategory[loc.category_id] || 'gray';
                    const iconClass = iconByCategory[loc.category_id] || 'bi bi-geo-alt-fill';
                    const marker = L.marker([loc.latitude, loc.longitude], {icon: createColoredIcon(colour, iconClass)})
                        .addTo(map);

                    marker.bindPopup(() => createPopUps(loc, marker));
                    mapMarkersById[loc.id] = marker;
                    if (datalist) {
                        const option = document.createElement('option');
                        option.value = loc.name;
                        datalist.appendChild(option);
                    }
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
        currentDisplayedRoutes = []; // Clear stored routes
        updateSelectedLocationsList();
    }

    //builds and displays the detailed information for each generated route in the panel below the map.
    // It includes the route's stats (satisfaction, distance), the list of locations, and a "Save Route" button for each route.
    function updateRouteDetailsUI() {
        if (!routesContainer) return;
        routesContainer.innerHTML = '';

        currentDisplayedRoutes.forEach((route, index) => {
            const routeDiv = document.createElement('div');
            routeDiv.className = 'route-card card app-card p-3';
            const distanceKm = route.distance ? (route.distance / 1000).toFixed(2) : '0.00';
            routeDiv.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <div class="fw-semibold">Route ${index + 1}</div>
                    <span class="small text-muted">${distanceKm} km · score ${route.satisfaction.toFixed(2)}</span>
                </div>`;
            const ul = document.createElement('ul');
            ul.className = 'list-unstyled mb-2';
            route.locations.forEach(loc => {
                const li = document.createElement('li');
                li.textContent = `${loc.name} `;
                li.className = 'small';
                ul.appendChild(li);
            });
            routeDiv.appendChild(ul);

            const saveButton = document.createElement('button');
            saveButton.className = 'btn btn-success btn-sm rounded-pill';
            saveButton.textContent = 'Save Route';
            saveButton.onclick = () => saveRoute(route.id);
            routeDiv.appendChild(saveButton);

            routesContainer.appendChild(routeDiv);
        });
    }

    function saveRoute(routeId) {
    const baseRoute = currentDisplayedRoutes.find(r => r.id === routeId);
    if (!baseRoute) {
        alert('Error: Could not find route data to save.');
        return;
    }

    const routeToSave = {
        ...baseRoute,
        travel_mode: currentTravelMode
    };

    fetch(`/save_route`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(routeToSave)
    })
    .then(async response => {
        if (response.status === 401) {
            let message = 'To save a route, sign up or login!';
            try {
                const data = await response.json();
                if (data && data.message) {
                    message = data.message;
                }
            } catch (error) {
                console.error('Error parsing auth response:', error);
            }
            alert(message);
            window.location.href = '/login';
            return null;
        }
        return response.json();
    })
    .then(data => {
        if (!data) return;
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


    //Redraws routes with a new mode of transport
    async function redrawRoutesWithNewMode(newMode) {
        if (currentDisplayedRoutes.length === 0) return;

        document.body.style.cursor = 'wait';
        resultsLayer.clearLayers();

        for (let i = 0; i < currentDisplayedRoutes.length; i++) {
            const route = currentDisplayedRoutes[i];
            const location_ids = route.locations.map(loc => loc.id);

            try {
                const response = await fetch('/api/recalculate_route', {    //Sends a request to the /api/recalculate_route endpoint with the location IDs and the new travel mode
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
                        style: { color: currentRouteColors[i % currentRouteColors.length], weight: 6, opacity: 0.75 }
                    }).addTo(resultsLayer);
                }
                route.locations.forEach(loc => {
                    const markerColor = loc.color || loc.colour || 'gray';
                    const iconByCategory = {
                        1: 'bi bi-cup-hot',
                        2: 'bi bi-bank2',
                        3: 'bi bi-bag',
                        4: 'bi bi-tree',
                        5: 'bi bi-palette',
                        6: 'bi bi-moon-stars'
                    };
                    const iconClass = iconByCategory[loc.category_id] || 'bi bi-geo-alt-fill';
                    const marker = L.marker([loc.latitude, loc.longitude], { icon: createColoredIcon(markerColor, iconClass) })
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

           //Loops through the received routes, drawing each path and its location markers on the map.
            currentDisplayedRoutes.forEach((route, index) => {
                if (route.geometry) {
                    L.geoJSON(route.geometry, {
                        style: { color: currentRouteColors[index % currentRouteColors.length], weight: 6, opacity: 0.75 }
                    }).addTo(resultsLayer);
                }
                route.locations.forEach(loc => {
                    const markerColor = loc.color || loc.colour || 'gray';
                    const iconByCategory = {
                        1: 'bi bi-cup-hot',
                        2: 'bi bi-bank2',
                        3: 'bi bi-bag',
                        4: 'bi bi-tree',
                        5: 'bi bi-palette',
                        6: 'bi bi-moon-stars'
                    };
                    const iconClass = iconByCategory[loc.category_id] || 'bi bi-geo-alt-fill';
                    const marker = L.marker([loc.latitude, loc.longitude], { icon: createColoredIcon(markerColor, iconClass) })
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
            alert('Failed to generate routes. Please try again.');
        })
        .finally(() => {
            document.body.style.cursor = 'default';
        });
    }

    const form = document.getElementById('category-form');
    if (form) {
        form.addEventListener('submit', function(event) {      //When the "Generate Routes" button is clicked, it prevents the page from reloading and calls the generateRoute function.
            event.preventDefault();
            const categoryID = document.getElementById('category_select').value;
            generateRoute(categoryID);
        });
    }

    const travelModeSelector = document.getElementById('travel-mode-selector');
    if (travelModeSelector) {
        const hexToRgba = (hex, alpha) => {
            const clean = hex.replace('#', '');
            const bigint = parseInt(clean, 16);
            const r = (bigint >> 16) & 255;
            const g = (bigint >> 8) & 255;
            const b = bigint & 255;
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
        };
        const setModeColor = (mode) => {
            const color = travelModeColors[mode] || travelModeColors.walking;
            travelModeSelector.style.setProperty('--mode-color', color);
            travelModeSelector.style.setProperty('--mode-shadow', hexToRgba(color, 0.35));
        };
        setModeColor(currentTravelMode);
        travelModeSelector.addEventListener('click', function(event) {
            const button = event.target.closest('.mode-btn');
            if (button) {
                travelModeSelector.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                currentTravelMode = button.dataset.mode;
                currentRouteColors = routeColorPalettes[currentTravelMode] || routeColorPalettes.walking;
                setModeColor(currentTravelMode);

                // Instead of regenerating routes which takes longer, just recalculates and redraws route when mode of transport changes
                redrawRoutesWithNewMode(currentTravelMode);
            }
        });
    }

    function highlightLocation(location) {
        const marker = mapMarkersById[location.id];
        if (!marker) return;

        const latlng = marker.getLatLng();
        map.setView(latlng, 16, { animate: true });
        marker.openPopup();
    }

    function findLocationByName(query) {
        const normalized = query.trim().toLowerCase();
        if (!normalized) return null;
        const locations = Object.values(allLocations);
        let match = locations.find(loc => loc.name.toLowerCase() === normalized);
        if (!match) {
            match = locations.find(loc => loc.name.toLowerCase().includes(normalized));
        }
        return match || null;
    }

    function showMissingLocationPanel(name) {
        const panel = document.getElementById('missing-location-panel');
        if (!panel) return;
        panel.classList.add('active');
        const nameInput = document.getElementById('missing-name');
        const message = document.getElementById('missing-location-message');
        const geoResult = document.getElementById('geocode-result');
        const queryInput = document.getElementById('missing-query');
        if (nameInput && name) {
            nameInput.value = name;
        }
        if (message) {
            message.textContent = '';
        }
        if (geoResult) {
            geoResult.classList.add('d-none');
            geoResult.textContent = '';
        }
        if (queryInput) {
            queryInput.value = '';
        }
        geocodedLocation = null;
    }

    function hideMissingLocationPanel() {
        const panel = document.getElementById('missing-location-panel');
        if (!panel) return;
        panel.classList.remove('active');
    }

    function addLocationOption(name) {
        const datalist = document.getElementById('location-search-list');
        if (!datalist) return;
        const option = document.createElement('option');
        option.value = name;
        datalist.appendChild(option);
    }

    const searchForm = document.getElementById('location-search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const input = document.getElementById('location-search-input');
            const match = findLocationByName(input.value);
            if (!match) {
                showMissingLocationPanel(input.value);
                return;
            }
            hideMissingLocationPanel();
            highlightLocation(match);
        });
    }

    const missingForm = document.getElementById('missing-location-form');
    if (missingForm) {
        missingForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const name = document.getElementById('missing-name').value.trim();
            const categoryId = document.getElementById('missing-category').value;
            const message = document.getElementById('missing-location-message');

            if (!name || !geocodedLocation) {
                if (message) {
                    message.textContent = 'Name and a valid lookup are required.';
                }
                return;
            }

            fetch('/api/locations/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name,
                    address: geocodedLocation.address || '',
                    latitude: geocodedLocation.latitude,
                    longitude: geocodedLocation.longitude,
                    category_id: categoryId
                })
            })
            .then(res => res.json().then(data => ({ ok: res.ok, data })))
            .then(({ ok, data }) => {
                if (!ok || !data.success) {
                    const errorMessage = data.message || 'Could not add location.';
                    if (message) message.textContent = errorMessage;
                    return;
                }

            const newLoc = data.location;
            allLocations[newLoc.id] = newLoc;
            addLocationOption(newLoc.name);

            const markerColor = newLoc.color || 'gray';
            const iconByCategory = {
                1: 'bi bi-cup-hot',
                2: 'bi bi-bank2',
                3: 'bi bi-bag',
                4: 'bi bi-tree',
                5: 'bi bi-palette',
                6: 'bi bi-moon-stars'
            };
            const iconClass = iconByCategory[newLoc.category_id] || 'bi bi-geo-alt-fill';
            const marker = L.marker([newLoc.latitude, newLoc.longitude], { icon: createColoredIcon(markerColor, iconClass) })
                .addTo(map);
                marker.bindPopup(() => createPopUps(newLoc, marker));
                mapMarkersById[newLoc.id] = marker;

                highlightLocation(newLoc);
                hideMissingLocationPanel();
                document.getElementById('location-search-input').value = newLoc.name;
            })
            .catch(() => {
                if (message) message.textContent = 'Could not add location.';
            });
        });
    }

    const lookupButton = document.getElementById('lookup-location-btn');
    if (lookupButton) {
        lookupButton.addEventListener('click', function() {
            const queryInput = document.getElementById('missing-query');
            const message = document.getElementById('missing-location-message');
            const geoResult = document.getElementById('geocode-result');
            const query = queryInput.value.trim();

            if (!query) {
                if (message) message.textContent = 'Paste a Google Maps link or address.';
                return;
            }

            if (message) message.textContent = '';
            fetch('/api/geocode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            })
            .then(res => res.json().then(data => ({ ok: res.ok, data })))
            .then(({ ok, data }) => {
                if (!ok || !data.success) {
                    geocodedLocation = null;
                    if (geoResult) {
                        geoResult.classList.add('d-none');
                        geoResult.textContent = '';
                    }
                    if (message) message.textContent = data.message || 'Lookup failed.';
                    return;
                }

                geocodedLocation = {
                    latitude: data.latitude,
                    longitude: data.longitude,
                    address: data.address || ''
                };

                if (geoResult) {
                    const addressText = geocodedLocation.address ? `Address: ${geocodedLocation.address}` : 'Address unavailable';
                    geoResult.textContent = `${addressText} · ${geocodedLocation.latitude.toFixed(5)}, ${geocodedLocation.longitude.toFixed(5)}`;
                    geoResult.classList.remove('d-none');
                }
            })
            .catch(() => {
                geocodedLocation = null;
                if (message) message.textContent = 'Lookup failed.';
            });
        });
    }

    const clearButton = document.getElementById('clearroute-btn');
    if (clearButton) {
        clearButton.addEventListener('click', clearMap);
    }

    fetchAndDisplayAllLocations(); // Calls fetchAndDisplayAllLocations() to load and display all the location markers when the page first loads.
});
