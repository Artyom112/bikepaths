window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature) {
            return {
                weight: 10,
                color: 'cyan',
                opacity: 0.6
            };
        },
        function1: function(feature, latlng) {
            return L.circleMarker(latlng, {
                radius: 4,
                fillColor: 'red',
                color: 'white',
                weight: 1,
                fillOpacity: 1
            });
        }

    }
});