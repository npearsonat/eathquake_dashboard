import streamlit as st
import pandas as pd
import plotly.express as px

# Streamlit page setup
st.set_page_config(layout="wide")
st.title("Global Earthquake Map")

# Load your earthquake data
# Replace with your actual data path
df = pd.read_csv("data/database.csv")

# Make sure column names match exactly
df.rename(columns=lambda x: x.lower(), inplace=True)

# Drop rows with missing lat/lon or magnitude
df = df.dropna(subset=['latitude', 'longitude', 'magnitude'])

# Show world map with quakes
fig = px.scatter_mapbox(
    df,
    lat="latitude",
    lon="longitude",
    size="magnitude",
    color="magnitude",
    size_max=30,
    zoom=0,
    mapbox_style="carto-darkmatter",  # Dark background for visual contrast
    color_continuous_scale="gray",    # Darker = stronger
    opacity=0.8,
    hover_name="magnitude"
)

fig.update_layout(
    margin=dict(l=0, r=0, t=0, b=0),
    coloraxis_colorbar=dict(
        title="Magnitude",
        tickvals=[4, 5, 6, 7]
    )
)

# Show the figure
st.plotly_chart(fig, use_container_width=True)
