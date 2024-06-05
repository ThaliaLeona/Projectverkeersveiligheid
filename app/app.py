from flask import Flask, render_template, request
import geopandas as gpd
import pandas as pd
import folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from geopy.distance import geodesic
import json
import os
import decimal

# GEOCODEREN ADRES
def geocodeAdres(adres):
    geolocator = Nominatim(user_agent="my_app")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    try:
        location = geocode(adres)
        if location:
            return location.latitude, location.longitude
        else:
            return None  #NONE ALS NIETS GEV W
    except Exception as e:
        print(f"Error occurred during geocoding: {e}")
        return None #NONE ALS NIETS GEV W

# ° DF VAN CSV INCL OMZETTING NR NUMERIEKE WAARDEN
df = pd.read_csv('C:/Users/Thalia Leona/Desktop/LAM2/SEM04/GEO-ICT/Project/Lagen/Onderwijs/csv/POI_aangepast.csv', delimiter=';', decimal=',')

# LIST WAARDEN IN KOLOMMEN CAT EN GEM 
unique_categories = df['CATEGORIE'].unique().tolist()
unique_gemeentes = df['GEMEENTE'].unique().tolist()

# GDF °
geometry = gpd.points_from_xy(df['WGS84_LONGITUDE'], df['WGS84_LATITUDE'])
gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

# URL'S IC
vlag_url = 'https://cdn-icons-png.freepik.com/256/81/81154.png?uid=R151608027&ga=GA1.1.1104440539.1717535425&semt=ais_hybrid'
trein_url = 'https://cdn-icons-png.freepik.com/256/88/88696.png?uid=R151608027&ga=GA1.1.1104440539.1717535425&semt=ais_hybrid'
bel_url = 'https://cdn-icons-png.freepik.com/256/162/162722.png?uid=R151608027&ga=GA1.1.1104440539.1717535425&semt=ais_hybrid'
oog_url = 'https://cdn-icons-png.freepik.com/256/58/58976.png?uid=R151608027&ga=GA1.1.1104440539.1717535425&semt=ais_hybrid'

# FLASK °
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        address = request.form.get("input_address")
        onderwijsniveau = request.form.get("tags-level")
        gemeente = request.form.get("input_gemeente")
        print("Filter inputs:", onderwijsniveau, gemeente)

        # FILTER GDF
        filtered_gdf = gdf[
            (gdf['CATEGORIE'] == onderwijsniveau) &
            (gdf['GEMEENTE'] == gemeente)
        ]
        print(f"Filtered DataFrame: {filtered_gdf}")

        # DEBUGGEN GEFILT LOC
        for index, row in filtered_gdf.iterrows():
            print(f"Location {index}: {row['NAAM']} - LAT: {row['WGS84_LATITUDE']}, LON: {row['WGS84_LONGITUDE']}")

        # GEOCODE THUISADRES
        map_center = geocodeAdres(address)
        if map_center:
            my_map = folium.Map(location=map_center, zoom_start=12, tiles=None)
            
                        # CARTODBPOSITRON = STANDAARD TEGELLAAG
            folium.TileLayer('cartodbpositron').add_to(my_map)
            folium.TileLayer('openstreetmap').add_to(my_map)

            # MARKERS ° VR GEFILT SCHOOLLOC
            for index, row in filtered_gdf.iterrows():
                location_coords = (row['WGS84_LATITUDE'], row['WGS84_LONGITUDE'])
                distance = geodesic(map_center, location_coords).km  # Calculate distance
                popup_content = (f"<b>{row['NAAM']}</b> {row['CATEGORIE']}, <i>{row['STRAAT']}</i>, "
                                 f"<i>{row['GEMEENTE']}</i><br><b>{row['LINK']}</b><br><b>Afstand van thuis:</b> {distance:.2f} km")
                marker = folium.Marker(
                    location_coords,
                    popup=popup_content,
                    icon=folium.Icon(icon="graduation-cap", prefix='fa')
                )
                marker.add_to(my_map)

            # MARKER ° THUISADRES
            folium.Marker(
                map_center,
                icon=folium.Icon(icon="home", color="darkblue", icon_color="white"),
                popup=folium.Popup(f'<b>Jouw adres:</b><br>{address}<br><b>coördinaten:</b><br>{map_center}')
            ).add_to(my_map)

            # GEOJSON F INLADEN + IC INFO LINKEN
            geojson_files = {
                "C:/Users/Thalia Leona/Desktop/LAM2/SEM04/GEO-ICT/Project/app/verkeerspunten/geel/TRAMOVERSTEEKPUNT.geojson": ("bell"),
                "C:/Users/Thalia Leona/Desktop/LAM2/SEM04/GEO-ICT/Project/app/verkeerspunten/bruin/SPOOROVERSTEEKPUNT.geojson": ("train"),
                "C:/Users/Thalia Leona/Desktop/LAM2/SEM04/GEO-ICT/Project/app/verkeerspunten/oranje/ZEBRAPAD_VERKEERSLICHT.geojson": ("eye"),
                "C:/Users/Thalia Leona/Desktop/LAM2/SEM04/GEO-ICT/Project/app/verkeerspunten/rood/GEVAARLIJK_PUNT.geojson": ("flag")
            }
            geojson_data = {}

            for filepath, (icon) in geojson_files.items():
                if os.path.exists(filepath):
                    with open(filepath) as f:
                        filename = os.path.basename(filepath)
                        geojson_data[filename] = json.load(f)
                        geojson_data[filename]["icon"] = icon
                else:
                    print(f"File not found: {filepath}")

            # GEOJSON DATA => JAVASCRIPT
            geojson_data_json = json.dumps(geojson_data)

            # JAVASCRIPT AANP IFV MARKERCLICKS
            my_map.get_root().html.add_child(folium.Element(f"""
                <script>
                    var geojsonData = {geojson_data_json};

                    function addPolygon(e) {{
                        var lat = e.latlng.lat;
                        var lng = e.latlng.lng;
                        var map = e.target._map;
                        var userLat = {map_center[0]};
                        var userLng = {map_center[1]};
                        var distance = L.latLng(userLat, userLng).distanceTo(L.latLng(lat, lng));
                        
                        // MIDDELPUNT THUISADRES - SCHOOLLOC BEREKENEN 
                        var midLat = (userLat + lat) / 2;
                        var midLng = (userLng + lng) / 2;

                        // VERWIJDER EVENTUELE BESTAANDE CIRKEL
                        if (map.existingCircle) {{
                            map.removeLayer(map.existingCircle);
                        }}

                        // VERWIJDER EVENTUELE BESTAANDE MARKERS
                        if (map.markers) {{
                            map.markers.forEach(marker => map.removeLayer(marker));
                        }}

                        map.markers = [];  // RESET MARKERVERZAMELING NR LEEG 

                        map.existingCircle = L.circle([midLat, midLng], {{
                            color: 'blue',
                            fillColor: 'blue',
                            fillOpacity: 0.2,
                            radius: distance / 2 
                        }}).addTo(map);                 
                        
                        function addMarkers(data) {{
                        // MARKERVERZAMELING DATA TOESCHR
                            for (var filename in data) {{
                                var features = data[filename].features;
                                var icon = data[filename].icon; // INL ICOON DAT GEKOPPELD W AAN FILE LOC

                                for (var i = 0; i < features.length; i++) {{
                                    var feature = features[i];
                                    var coords = feature.geometry.coordinates;
                                    var latLng = L.latLng(coords[1], coords[0]);

                                    if (map.existingCircle.getBounds().contains(latLng)) {{
                                        var marker = L.marker(latLng, {{
                                            icon: L.divIcon({{
                                                className: 'custom-div-icon',
                                                html: '<i class="fa fa-' + icon + ' fa-2x"></i>'
                                            }})
                                        }}).addTo(map).bindPopup("<b>" + filename.replace("_", " ").replace(".geojson", "") + "</b>");
                                        
                                        map.markers.push(marker); // Add marker to array
                                    }}
                                }}
                            }}
                        }}                                                                    
                        addMarkers(geojsonData);
                    }}
                    // KLIK-EVENTLISTENERS LINKEN AAN ALLE MARKERS
                    function addClickListenersToMarkers() {{
                        var map = {my_map.get_name()};
                        map.eachLayer(function(layer) {{
                            if (layer instanceof L.Marker) {{
                                layer.on('click', addPolygon);
                            }}
                        }});
                    }}

                    // ! KAART M VOLL GELADEN ZIJN VOOR TOEV !
                    document.addEventListener('DOMContentLoaded', function() {{
                        addClickListenersToMarkers();
                    }});
                </script>
            """))

            # DEF + ° LEGENDE 
            legende_html = f'''
            <div style="position: fixed; 
            bottom: 320px; left: 50px; width: 230px; height: 140px; 
            border:2px solid grey; z-index:99999; font-size:14px;
            background-color:white; padding: 10px;
            ">
            &nbsp; <u><b>LEGENDE</b></u> <br><br>
            &nbsp; <img src="{vlag_url}" alt="Vlag icoon" style="width:20px;height:20px;">&nbsp; gevaarlijk punt<br>
            &nbsp; <img src="{bel_url}" alt="bel icoon" style="width:20px;height:20px;">&nbsp; tramoversteekpunt<br>
            &nbsp; <img src="{trein_url}" alt="trein icoon" style="width:20px;height:20px;">&nbsp; spooroversteekpunt<br>
            &nbsp; <img src="{oog_url}" alt="licht icoon" style="width:20px;height:20px;">&nbsp; zebrapad met verkeerslicht<br>
            </div>
            '''
            print("Adding legend to map:")
            print(legende_html)
            my_map.get_root().html.add_child(folium.Element(legende_html))

            # ° REDRAW NA EVENTUELE VERTRAGING
            my_map.get_root().html.add_child(folium.Element(f"""
            <script>
                setTimeout(function() {{
                    map.invalidateSize();
                }}, 100);
            </script>
            """))
            
            # ° TILEKEUZEVENSTER (2 VENSTERS MGLK)
            folium.LayerControl().add_to(my_map)

            return render_template("kaart.html", folium_map=my_map._repr_html_(), categories=unique_categories, gemeentes=unique_gemeentes)
        else:
            print("Geocoding failed for address:", address)
            return render_template("kaartapplicatie.html", error="Geocoding mislukt. Controleer het adres.", categories=unique_categories, gemeentes=unique_gemeentes)
    else:
        return render_template("kaartapplicatie.html", categories=unique_categories, gemeentes=unique_gemeentes)

if __name__ == "__main__":
    app.run(debug=True, port=8080)