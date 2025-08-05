import streamlit as st
import pandas as pd
import plotly.express as px

# Load your earthquake data
# Make sure your DataFrame has 'latitude', 'longitude', and 'magnitude' columns
df = pd.read_csv("data/database.csv")

# Adjust magnitude scaling (smaller bubbles for small quakes)
df["size"] = df["Magnitude"] ** 2  # Adjust this if sizes are too big

# Create the map
fig = px.scatter_mapbox(
    df,
    lat="latitude",
    lon="longitude",
    size="size",
    color="magnitude",
    color_continuous_scale="YlOrRd",
    hover_name="place" if "place" in df.columns else None,
    zoom=1,
    height=700,
    mapbox_style="carto-positron"  # No token needed
)

fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

# Display it in Streamlit
st.plotly_chart(fig, use_container_width=True)
