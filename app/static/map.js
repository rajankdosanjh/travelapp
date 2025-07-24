let map = L.map('map').setView([51.5074, -0.1278], 13); // Centered on London

// OpenStreetMap Tile
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

let markerList = [];
let routeLayer = null;

fetch('/api/locations')
  .then(res => res.json())
  .then(locations => {
    const ColoursbyCategory = {
      'Food and Drink' : 'red',
      'History': 'blue',
      'Shopping': 'green',
      'Nature': 'orange',
      'Culture': 'purple',
      'Nightlife': 'yellow'
    };
    locations.forEach(loc => {
      const colour = ColoursbyCategory[loc.category] || 'gray';
      const marker = L.marker([loc.latitude, loc.longitude], {
        icon: L.divIcon({
          className: 'custom-icon',
          html: `<div style="background:${colour}; width:12px; height:12px; border-radius:50%;"></div>`
        })
      }).addTo(map);

      marker.bindPopup(`<b>${loc.name}</b><br><b>${loc.category}</b></br><br><button onclick="addToRoute(${loc.longitude}, ${loc.latitude})">Add to Route</button>`);
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
  });
}