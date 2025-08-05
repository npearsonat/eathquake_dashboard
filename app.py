import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Earthquake Data Explorer")

@st.cache_data
def load_data():
    df = pd.read_csv("global_disaster_dashboard/data/database.csv")
    df['Datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce')
    return df

df = load_data()

st.write(f"Loaded {len(df):,} earthquake records.")

# Map with points colored by Magnitude
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

st.plotly_chart(fig, use_container_width=True)
