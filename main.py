import dash
from dash import html, Output, Input, State
import dash_leaflet as dl
import json
import os
import geopandas as gpd
from shapely.geometry import shape, Point

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


def feature_closest_to_click(click_latlng, geojson):
    """Pick the GeoJSON feature whose geometry is nearest to the clicked point."""
    if not geojson or "features" not in geojson or not click_latlng:
        return None
    lat, lon = float(click_latlng[0]), float(click_latlng[1])
    pt = Point(lon, lat)
    best_feature, best_d = None, float("inf")
    for f in geojson["features"]:
        try:
            d = shape(f["geometry"]).distance(pt)
        except (KeyError, TypeError, ValueError):
            continue
        if d < best_d:
            best_d, best_feature = d, f
    return best_feature


def feature_from_cycle_click(click_data, geojson):
    """
    dash-leaflet passes the clicked GeoJSON feature as clickData (see GeoJSON.tsx _getFeature),
    not {latlng: ...}. Fall back to nearest-feature search if only a map-style payload is present.
    """
    if not click_data:
        return None
    if isinstance(click_data, dict) and click_data.get("geometry") is not None:
        return click_data
    latlng = click_data.get("latlng")
    return feature_closest_to_click(latlng, geojson)


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

            # Метро ниже — клики по линии попадают в верхний слой велодорожек
            dl.LayerGroup(id="metro-layer", children=metro_markers),

            dl.GeoJSON(
                data=cycle_geojson,
                id="cycle-layer",
                options=dict(style=dict(color="darkblue", weight=4, opacity=0.8)),
                hoverStyle=dict(weight=8, color="cyan"),
            ),
            
            # Контейнер для попапа
            html.Div(id="popup-container")
        ]
    )
])

# --- 4. CALLBACK ДЛЯ КЛИКА ---
# dash-leaflet GeoJSON: используем n_clicks + clickData (свойства click_feature нет)
@app.callback(
    Output("popup-container", "children"),
    Input("cycle-layer", "n_clicks"),
    State("cycle-layer", "clickData"),
    prevent_initial_call=True,
)
def handle_click(_n, click_data):
    if metro_gdf is None or not cycle_geojson:
        return None
    feature = feature_from_cycle_click(click_data, cycle_geojson)
    if not feature:
        return None

    line_geom = shape(feature["geometry"])
    
    # Расчет расстояний
    distances = []
    for _, row in metro_gdf.iterrows():
        station_geom = row.geometry
        # Коэффициент для Москвы (градусы -> метры)
        d = line_geom.distance(station_geom) * 85000
        name = row.get('name') or row.get('name:ru') or "Станция"
        distances.append({'name': name, 'dist': d})
    
    # Три ближайших станции по расстоянию до линии (по возрастанию)
    top_3 = sorted(distances, key=lambda x: x['dist'])[:3]

    content = [
        html.B("Ближайшие станции метро (по возрастанию расстояния):"),
        html.Br(),
    ]
    for s in top_3:
        content.append(f"{s['name']}: {int(s['dist'])} м")
        content.append(html.Br())
    
    centroid = line_geom.centroid
    return dl.Popup(
        children=html.Div(content),
        position=[centroid.y, centroid.x],
    )

if __name__ == '__main__':
    app.run(debug=True, port=8051)