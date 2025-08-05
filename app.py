import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")
st.title("Global Earthquake Map")

# Load earthquake data
df = pd.read_csv("data/database.csv")
df.rename(columns=lambda x: x.lower(), inplace=True)
df = df.dropna(subset=['latitude', 'longitude', 'magnitude'])

# Tweak marker size by scaling magnitude
# You can fine-tune this multiplier
df["size"] = df["magnitude"] ** 2

# Use a cleaner map style
fig = px.scatter_mapbox(
    df,
    lat="latitude",
    lon="longitude",
    size="size",
    color="magnitude",
    size_max=15,                         # Keep small for less visual clutter
    zoom=1,                              # Decent zoom level for full globe
    mapbox_style="open-street-map",      # Clean, bright background
    color_continuous_scale="OrRd",       # Orange-Red for heat/magnitude
    hover_name="magnitude",
    opacity=0.6,
    center={"lat": 0, "lon": 0}
)

fig.update_layout(
    margin=dict(l=0, r=0, t=0, b=0),
    mapbox=dict(
        zoom=1,
        center={"lat": 0, "lon": 0},
        style="open-street-map"
    ),
    coloraxis_colorbar=dict(
        title="Magnitude"
    )
)

st.plotly_chart(fig, use_container_width=True)
