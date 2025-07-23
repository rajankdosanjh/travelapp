let map = L.map('map').setView([51.5074, -0.1278], 13); // Centered on London

// Add OpenStreetMap tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

let markerList = [];
let routeLayer = null;

// On map click, add marker
map.on('click', function(e) {
  const latlng = e.latlng;
  const marker = L.marker(latlng).addTo(map);
  markerList.push([latlng.lng, latlng.lat]); // ORS uses [lng, lat]
});

// Display the route using ORS
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
      style: { color: 'pink', weight: 5 }
    }).addTo(map);
    map.fitBounds(routeLayer.getBounds());
  })
  .catch(error => {
    console.error('ORS Routing error:', error);
    alert('Failed to generate route. Check your API key and network.');
  });
}
