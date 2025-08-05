import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import requests

st.set_page_config(layout="wide")
st.title("Global Earthquake Map with Terrain & Borders")

# Load earthquake data
df = pd.read_csv("data/database.csv")
df.rename(columns=lambda x: x.lower(), inplace=True)
df = df.dropna(subset=['latitude', 'longitude', 'magnitude'])
df["size"] = df["magnitude"] ** 2

# Load country borders geojson
url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
borders = requests.get(url).json()

# Base map with satellite terrain
fig = px.scatter_mapbox(
    df,
    lat="latitude",
    lon="longitude",
    size="size",
    color="magnitude",
    size_max=15,
    zoom=1,
    opacity=0.6,
    mapbox_style="satellite-streets",
    hover_name="magnitude",
    color_continuous_scale="OrRd",
    center={"lat": 0, "lon": 0}
)

# Add country borders as overlay
fig.update_layout(
    mapbox=dict(
        layers=[
            dict(
                sourcetype="geojson",
                source=borders,
                type="line",
                color="white",
                line=dict(width=1),
            )
        ],
        center={"lat": 0, "lon": 0},
        zoom=1,
        style="satellite-streets"
    ),
    margin=dict(l=0, r=0, t=0, b=0),
    coloraxis_colorbar=dict(title="Magnitude")
)

st.plotly_chart(fig, use_container_width=True)
