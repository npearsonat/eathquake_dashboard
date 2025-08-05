import streamlit as st
import pandas as pd
import plotly.express as px
import json

@st.cache_data
def load_data():
    df = pd.read_csv("data/database.csv")
    df['Datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce')
    return df

def load_geojson():
    with open("data/tectonic_boundaries.json") as f:
        return json.load(f)

df = load_data()
geojson = load_geojson()

fig = px.scatter_mapbox(
    df,
    lat="Latitude",
    lon="Longitude",
    color="Magnitude",
    size="Magnitude",
    hover_name="Date",
    hover_data=["Magnitude", "Depth"],
    color_continuous_scale="Viridis",
    size_max=15,
    zoom=1,
    mapbox_style="open-street-map"
)

fig.update_layout(
    geojson=geojson,
    geo=dict(
        visible=False,
        lakecolor="rgb(255, 255, 255)"
    )
)

st.plotly_chart(fig, use_container_width=True)
