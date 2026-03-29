import dash
from dash import html, dcc, Output, Input
import dash_leaflet as dl
import json
import os
import geopandas as gpd
from shapely.geometry import shape

# --- 1. ЗАГРУЗКА ДАННЫХ ---
CYCLING_DATA_FILE = "moscow_cycling.json"
METRO_DATA_FILE = "moscow_metro.json"

def load_data():
    if not os.path.exists(CYCLING_DATA_FILE) or not os.path.exists(METRO_DATA_FILE):
        return {}, [], None
    
    with open(CYCLING_DATA_FILE, 'r') as f:
        c_geojson = json.load(f)
    with open(METRO_DATA_FILE, 'r') as f:
        m_geojson = json.load(f)
    
    m_gdf = gpd.read_file(METRO_DATA_FILE)
    return c_geojson, m_geojson, m_gdf

# Загружаем данные один раз
cycle_geojson, metro_geojson, metro_gdf = load_data()

# --- 2. ПОДГОТОВКА СЛОЕВ (выносим из layout, чтобы не запутаться в скобках) ---

# Генерируем список красных точек метро заранее
metro_markers = []
if 'features' in metro_geojson:
    for f in metro_geojson['features']:
        if f['geometry']['type'] == 'Point':
            coords = f['geometry']['coordinates']
            name = f['properties'].get('name') or f['properties'].get('name:ru') or "Станция"
            
            marker = dl.CircleMarker(
                center=[coords[1], coords[0]],
                radius=5,
                fillColor="red",
                color="white",
                weight=1,
                fillOpacity=1,
                children=[dl.Tooltip(name)]
            )
            metro_markers.append(marker)

# --- 3. ИНТЕРФЕЙС ПРИЛОЖЕНИЯ ---
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H2("Аналитика: Велодорожки и Метро Москвы", 
            style={'fontFamily': 'sans-serif', 'padding': '15px'}),
    
    dl.Map(
        style={'width': '100%', 'height': '85vh'}, 
        center=[55.7558, 37.6173], 
        zoom=12, 
        children=[
            # Слой карты
            dl.TileLayer(url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"),
            
            # Слой велодорожек
            dl.GeoJSON(
                data=cycle_geojson,
                id="cycle-layer",
                options=dict(style=dict(color="darkblue", weight=4, opacity=0.8)),
                hoverStyle=dict(weight=8, color="cyan")
            ),
            
            # Слой метро (уже готовый список маркеров)
            dl.LayerGroup(id="metro-layer", children=metro_markers),
            
            # Контейнер для попапа
            html.Div(id="popup-container")
        ]
    )
])

# --- 4. CALLBACK ДЛЯ КЛИКА ---
@app.callback(
    Output("popup-container", "children"),
    Input("cycle-layer", "click_feature")
)
def handle_click(feature):
    if not feature or metro_gdf is None:
        return None

    # Геометрия линии
    line_geom = shape(feature['geometry'])
    
    # Расчет расстояний
    distances = []
    for _, row in metro_gdf.iterrows():
        station_geom = row.geometry
        # Коэффициент для Москвы (градусы -> метры)
        d = line_geom.distance(station_geom) * 85000
        name = row.get('name') or row.get('name:ru') or "Станция"
        distances.append({'name': name, 'dist': d})
    
    # ТОП-3 ближайших, сортировка по УБЫВАНИЮ расстояния (ТЗ)
    top_3 = sorted(distances, key=lambda x: x['dist'])[:3]
    top_3_desc = sorted(top_3, key=lambda x: x['dist'], reverse=True)
    
    # Контент попапа
    content = [html.B("Ближайшее метро:"), html.Br()]
    for s in top_3_desc:
        content.append(f"{s['name']}: {int(s['dist'])} м")
        content.append(html.Br())
    
    centroid = line_geom.centroid
    return dl.Popup(
        children=html.Div(content),
        position=[centroid.y, centroid.x],
        opened=True
    )

if __name__ == '__main__':
    app.run(debug=True)