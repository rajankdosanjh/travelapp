let map = L.map('map').setView([51.5074, -0.1278], 13); // Centered on London

// OpenStreetMap Tile
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

let markerList = [];
let routeLayer = null;

fetch('/api/locations')
  .then(res => res.json())
  .then(location => {
    const ColoursbyCategory = {
      'Food and Drink' : 'red',
      'History': 'blue',
      'Shopping': 'green',
      'Nature': 'orange',
      'Culture': 'purple',
      'Nightlife': 'black'
    };
    location.forEach(loc => {
      const colour = ColoursbyCategory[loc.category] || 'gray';
      const marker = L.marker([loc.latitude, loc.longitude], {
        icon: L.divIcon({
          className: 'custom-icon',
          html: `<div style="background:${colour}; width:12px; height:12px; border-radius:50%;"></div>`
        })
      }).addTo(map);

      marker.bindPopup(`<b>${loc.name}</b><br><b>${loc.category}</b></br><b>Tiktok Satisfaction Rating: ${loc.tiktok_rating}</b> <button onclick="addToRoute(${loc.longitude}, ${loc.latitude})">Add to Route</button>`);
    });
  })
  .catch(err => console.error(err));

function addToRoute(lng, lat) {
  markerList.push([lng, lat]);
}

// Displays the route using ORS
function displayRoute() {
  if (markerList.length < 2) {
    alert('Please select at least two points.');
    return;
  }

  fetch('https://api.openrouteservice.org/v2/directions/foot-walking/geojson', {
    method: 'POST',
    headers: {
      'Authorization': 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImRhNjdmYWZhYmE2ZTQ1MzA5ZjNlMDBmYTllMjkwMGJjIiwiaCI6Im11cm11cjY0In0=',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      coordinates: markerList
    })
  })
  .then(response => response.json())
  .then(data => {
    if (routeLayer) {
      map.removeLayer(routeLayer);
    }
    routeLayer = L.geoJSON(data, {
      style: { color: 'blue', weight: 5 }
    }).addTo(map);
    map.fitBounds(routeLayer.getBounds());
  })
  .catch(error => {
    console.error('ORS Routing error:', error);
    alert('Failed to generate route. Check your API key and network.');

    function clearMap() {
      resultsLayer.clearLayers();
      map.setView([51.5074, -0.1278], 13); // Reset map view
    }

    document.addEventListener('DOMContentLoaded', function () {
      // Find the form on the page by its ID
      const form = document.getElementById('category-form');
      if (form) {
        // Listen for the 'submit' event
        form.addEventListener('submit', function (event) {
          // Prevent the default form submission, which would cause a page reload
          event.preventDefault();

          // Get the selected category ID from the dropdown menu
          const categoryId = document.getElementById('category_select').value;

          // Call our main function to generate the route
          generateRoute(categoryId);
        });
      }
    });
  })}