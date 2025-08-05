import streamlit as st
import pandas as pd
import plotly.express as px

# Load your earthquake data
# Make sure your DataFrame has 'latitude', 'longitude', and 'magnitude' columns
df = pd.read_csv("data/database.csv")

# Base size for magnitude 5 (smallest you want)
base_size = 1
df["size"] = base_size * (2 ** (df["Magnitude"] - 5))
df["size"] = df["size"].clip(lower=base_size)

# Create the map
fig = px.scatter_mapbox(
    df,
    lat="Latitude",       
    lon="Longitude",        
    size="Magnitude",
    color="Magnitude",
    zoom=.5,
    height=600,
    mapbox_style="open-street-map"  
)

fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

# Display it in Streamlit
st.plotly_chart(fig, use_container_width=True)
