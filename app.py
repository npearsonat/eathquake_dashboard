import streamlit as st
import pandas as pd
import plotly.express as px
import json
import plotly.graph_objects as go

@st.cache_data
def load_data():
    df = pd.read_csv("data/database.csv")
    df['Datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce')
    return df

def load_geojson():
    with open("data/PB2002_boundaries.json") as f:
        return json.load(f)

df = load_data()
geojson = load_geojson()

fig.update_layout(
    mapbox_style="open-street-map",
    mapbox_zoom=1,
    mapbox_center={"lat": 0, "lon": 0},
    margin={"r":0,"t":0,"l":0,"b":0}
)

# Add the tectonic plate boundaries as a Scattermapbox trace
for feature in geojson['features']:
    coords = feature['geometry']['coordinates']
    # Flatten coords if they are nested (LineStrings)
    if feature['geometry']['type'] == 'LineString':
        lons, lats = zip(*coords)
        fig.add_trace(go.Scattermapbox(
            lon=lons,
            lat=lats,
            mode='lines',
            line=dict(width=2, color='red'),
            name='Tectonic Boundary'
        ))
    # You can add support for MultiLineString if needed

st.plotly_chart(fig, use_container_width=True)
