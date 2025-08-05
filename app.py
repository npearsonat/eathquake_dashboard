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

fig = px.scatter_mapbox(
    df,
    lat='Latitude',
    lon='Longitude',
    size='Magnitude',
    color='Magnitude',
    color_continuous_scale='Viridis',
    size_max=15,
    zoom=1,
    mapbox_style="open-street-map"
)

# Add tectonic plate boundaries as lines from geojson
for feature in geojson['features']:
    if feature['geometry']['type'] == 'LineString':
        lons, lats = zip(*feature['geometry']['coordinates'])
        fig.add_trace(go.Scattermapbox(
            lon=lons,
            lat=lats,
            mode='lines',
            line=dict(color='red', width=2),
            name='Tectonic Plate Boundary'
        ))

fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

st.plotly_chart(fig, use_container_width=True)
