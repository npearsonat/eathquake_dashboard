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
    lat="Latitude",         # capitalized
    lon="Longitude",        # capitalized
    size="Magnitude",
    color="Magnitude",
    zoom=1,
    height=600,
    mapbox_style="stamen-terrain"  # no token needed
)

fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

# Display it in Streamlit
st.plotly_chart(fig, use_container_width=True)
