/************************************
 Written by Ethan Gruber, egruber@numismatics.org
 Library: jQuery, Leaflet
 Date modified: May 2025
 Description: Display the Leaflet map on the browse page, based on the Solr query
 ************************************/
$(document).ready(function () {
    uri = getURLParameter('uri')
    
    if ($('#map').length > 0) {
        initialize_map(uri);
    }
    
    const data = {
        manifest: $('#iiif-manifest').text(),
        embedded: true // needed for codesandbox frame
    };
    
    uv = UV.init("uv", data);
});

function initialize_map(uri) {
    //initialize Leaflet and call GeoJSON via ajax
    var osm = L.tileLayer(
    'http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: 'OpenStreetMap',
        maxZoom: 8
    });
    
    var map = new L.Map('map', {
        center: new L.LatLng(0, 0),
        zoom: 4,
        layers:[osm]
    });
    
    var pointLayer = L.geoJson.ajax("getGeo?uri=" + uri, {
        onEachFeature: onEachFeature,
        pointToLayer: renderPoints
    }).addTo(map);
    
    pointLayer.on('data:loaded', function () {
        map.fitBounds(pointLayer.getBounds());
    }.bind(this));
    
    /*****
     * Features for manipulating layers
     *****/
    function renderPoints(feature, latlng) {
        var fillColor;
        switch (feature.properties.type) {
            case 'productionPlace':
            fillColor = '#6992fd';
            break;
            case 'subjectPlace':
            fillColor = '#a1d490';
        }
        
        return new L.CircleMarker(latlng, {
            radius: 5,
            fillColor: fillColor,
            color: "#000",
            weight: 1,
            opacity: 1,
            fillOpacity: 0.6
        });
    }
    
    function onEachFeature (feature, layer) {
        var type = feature.properties.type == 'productionPlace' ? 'Production Place': 'Subject Place';
        var label = feature.name;
        
        str = '<strong> ' + type + ':</strong>' + '<a href="' + feature.properties.gazetteer_uri + '">' + label + '</a>';
        
        layer.bindPopup(str);
    }
}

function getURLParameter(name) {
    return decodeURI(
    (RegExp(name + '=' + '(.+?)(&|$)').exec(location.search) ||[, null])[1]);
}