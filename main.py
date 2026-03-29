import dash
from dash import html
import dash_leaflet as dl
import osmnx as ox
import json
import os
from dash_extensions.javascript import assign

# Константы
CYCLING_DATA_FILE = "moscow_cycling.json"
METRO_DATA_FILE = "moscow_metro.json"
MOSCOW_CENTER = [55.7558, 37.6173]

def get_data():
    if not os.path.exists(CYCLING_DATA_FILE):
        print("Загрузка велодорожек...")
        tags_cycle = {'cycleway': True, 'highway': 'cycleway', 'bicycle': 'yes'}
        gdf_cycle = ox.features_from_place("Moscow, Russia", tags=tags_cycle)
        gdf_cycle = gdf_cycle[gdf_cycle.geometry.type.isin(['LineString', 'MultiLineString'])]
        with open(CYCLING_DATA_FILE, 'w') as f:
            json.dump(json.loads(gdf_cycle.to_json()), f)

    if not os.path.exists(METRO_DATA_FILE):
        print("Загрузка станций метро...")
        tags_metro = {'station': 'subway'}
        gdf_metro = ox.features_from_place("Moscow, Russia", tags=tags_metro)
        gdf_metro = gdf_metro[gdf_metro.geometry.type == 'Point']
        with open(METRO_DATA_FILE, 'w') as f:
            json.dump(json.loads(gdf_metro.to_json()), f)

    with open(CYCLING_DATA_FILE, 'r') as f:
        cycle_geojson = json.load(f)
    with open(METRO_DATA_FILE, 'r') as f:
        metro_geojson = json.load(f)
        
    return cycle_geojson, metro_geojson

cycle_data, metro_data = get_data()

# Обновленная JS-функция: теперь она берет имя из свойств объекта и вешает Popup
point_to_layer = assign("""
function(feature, latlng) {
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
""")

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H2("Транспортная инфраструктура: Станции и Веломаршруты", 
            style={'fontFamily': 'sans-serif', 'padding': '15px', 'margin': '0'}),
    
    dl.Map(
        style={'width': '100%', 'height': '90vh'}, 
        center=MOSCOW_CENTER, 
        zoom=13, 
        children=[
            dl.TileLayer(
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                attribution='&copy; OpenStreetMap'
            ),
            
            # Велодорожки
            dl.GeoJSON(
                data=cycle_data,
                options=dict(style=dict(color="darkblue", weight=3, opacity=0.6))
            ),
            
            # Станции метро с интерактивными попапами
            dl.GeoJSON(
                data=metro_data,
                options=dict(pointToLayer=point_to_layer)
            )
        ]
    )
], style={'padding': '0', 'margin': '0'})

if __name__ == '__main__':
    app.run(debug=True)