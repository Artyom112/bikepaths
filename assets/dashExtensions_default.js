window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, latlng) {
            // Получаем название станции, если оно есть в данных
            const name = feature.properties.name || "Станция метро";

            // Создаем маркер
            const marker = L.circleMarker(latlng, {
                radius: 6,
                fillColor: 'red',
                color: 'white',
                weight: 1,
                fillOpacity: 0.9
            });

            // Привязываем всплывающее окно (Popup)
            marker.bindPopup(`<b>${name}</b>`);

            return marker;
        }

    }
});