import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Global Earthquake Dashboard",
    page_icon="🌍",
    layout="wide"
)

# Title and description
st.title("🌍 Global Earthquake Dashboard")
st.markdown("**Real-time visualization of earthquake activity worldwide**")

# Load earthquake data
@st.cache_data
def load_data():
    df = pd.read_csv("data/database.csv")
    
    # Convert date column to datetime (adjust column name as needed)
    # Common date column names in earthquake datasets
    date_columns = ['Date', 'date', 'DateTime', 'datetime', 'Time', 'time']
    date_col = None
    
    for col in date_columns:
        if col in df.columns:
            date_col = col
            break
    
    if date_col:
        df['DateTime'] = pd.to_datetime(df[date_col], errors='coerce')
    else:
        # If no date column found, create a dummy one for demonstration
        st.warning("No date column found. Using dummy dates for demonstration.")
        df['DateTime'] = pd.date_range(start='2020-01-01', periods=len(df), freq='D')
    
    # Remove rows with invalid coordinates or magnitudes
    df = df.dropna(subset=['Latitude', 'Longitude', 'Magnitude', 'DateTime'])
    
    return df

# Function to assign country based on coordinates (simplified approach)
@st.cache_data
def assign_countries(df):
    """
    Assign countries to earthquakes based on coordinates.
    This is a simplified approach using coordinate ranges.
    For production, consider using a proper geocoding service.
    """
    df = df.copy()
    
    # Initialize country column
    df['Country'] = 'Unknown'
    
    # Define approximate coordinate ranges for major earthquake-prone countries
    # These are simplified bounding boxes - real implementation would use proper boundaries
    country_bounds = {
        'Japan': {'lat': (24, 46), 'lon': (123, 146)},
        'Indonesia': {'lat': (-11, 6), 'lon': (95, 141)},
        'Chile': {'lat': (-56, -17), 'lon': (-76, -66)},
        'United States': {'lat': (25, 49), 'lon': (-180, -66)},  # Including Alaska
        'Mexico': {'lat': (14, 33), 'lon': (-118, -86)},
        'Turkey': {'lat': (36, 42), 'lon': (26, 45)},
        'Iran': {'lat': (25, 40), 'lon': (44, 64)},
        'Peru': {'lat': (-18, 0), 'lon': (-82, -68)},
        'Greece': {'lat': (34, 42), 'lon': (19, 30)},
        'Italy': {'lat': (36, 47), 'lon': (6, 19)},
        'Philippines': {'lat': (4, 21), 'lon': (116, 127)},
        'New Zealand': {'lat': (-47, -34), 'lon': (166, 179)},
        'China': {'lat': (18, 54), 'lon': (73, 135)},
        'India': {'lat': (6, 37), 'lon': (68, 97)},
        'Afghanistan': {'lat': (29, 39), 'lon': (60, 75)},
        'Russia': {'lat': (41, 82), 'lon': (19, 180)},
        'Papua New Guinea': {'lat': (-12, -1), 'lon': (140, 157)},
        'Ecuador': {'lat': (-5, 2), 'lon': (-92, -75)},
        'Guatemala': {'lat': (13, 18), 'lon': (-93, -88)},
        'Costa Rica': {'lat': (8, 11), 'lon': (-86, -82)}
    }
    
    # Assign countries based on coordinate ranges
    for country, bounds in country_bounds.items():
        mask = (
            (df['Latitude'] >= bounds['lat'][0]) & 
            (df['Latitude'] <= bounds['lat'][1]) &
            (df['Longitude'] >= bounds['lon'][0]) & 
            (df['Longitude'] <= bounds['lon'][1])
        )
        df.loc[mask, 'Country'] = country
    
    return df

if page == "🌍 Global Map":

try:
    df = load_data()
    
    # Sidebar controls
    st.sidebar.header("🎛️ Controls")
    
    # Time range slider
    if not df.empty and 'DateTime' in df.columns:
        min_date = df['DateTime'].min().date()
        max_date = df['DateTime'].max().date()
        
        st.sidebar.subheader("📅 Time Range")
        date_range = st.sidebar.date_input(
            "Select date range:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        # Handle single date selection
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date = end_date = date_range
    
    # Magnitude filter
    st.sidebar.subheader("📊 Magnitude Range")
    min_mag = float(df['Magnitude'].min())
    max_mag = float(df['Magnitude'].max())
    
    magnitude_range = st.sidebar.slider(
        "Minimum magnitude to display:",
        min_value=min_mag,
        max_value=max_mag,
        value=min_mag,
        step=0.1,
        help="Higher magnitudes represent exponentially more powerful earthquakes"
    )
    
    # Filter data based on selections
    if 'DateTime' in df.columns:
        mask = (
            (df['DateTime'].dt.date >= start_date) & 
            (df['DateTime'].dt.date <= end_date) &
            (df['Magnitude'] >= magnitude_range)
        )
        filtered_df = df[mask].copy()
    else:
        filtered_df = df[df['Magnitude'] >= magnitude_range].copy()
    
    # Display statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Earthquakes", len(filtered_df))
    
    with col2:
        if not filtered_df.empty:
            st.metric("Max Magnitude", f"{filtered_df['Magnitude'].max():.1f}")
        else:
            st.metric("Max Magnitude", "N/A")
    
    with col3:
        if not filtered_df.empty:
            st.metric("Avg Magnitude", f"{filtered_df['Magnitude'].mean():.1f}")
        else:
            st.metric("Avg Magnitude", "N/A")
    
    with col4:
        major_earthquakes = len(filtered_df[filtered_df['Magnitude'] >= 7.0])
        st.metric("Major Quakes (7.0+)", major_earthquakes)
    
    if filtered_df.empty:
        st.warning("No earthquakes found for the selected criteria. Try adjusting your filters.")
    else:
        # Enhanced size calculation to emphasize high magnitudes
        # Using exponential scaling since Richter scale is logarithmic
        base_size = 3
        # Exponential scaling: each magnitude unit increases size dramatically
        filtered_df["size"] = base_size * (3 ** (filtered_df["Magnitude"] - min_mag))
        
        # Cap maximum size to prevent overwhelming visualization
        max_size = 100
        filtered_df["size"] = filtered_df["size"].clip(upper=max_size)
        
        # Create custom color scale that emphasizes high magnitudes
        # Use a non-linear color mapping
        magnitude_normalized = (filtered_df["Magnitude"] - filtered_df["Magnitude"].min()) / (filtered_df["Magnitude"].max() - filtered_df["Magnitude"].min())
        # Apply power transformation to emphasize high values
        color_values = magnitude_normalized ** 0.5  # Square root makes high values more prominent
        
        # Create the enhanced map
        fig = px.scatter_mapbox(
            filtered_df,
            lat="Latitude",       
            lon="Longitude",        
            size="size",
            color="Magnitude",
            hover_name="Magnitude",
            hover_data={
                "Magnitude": ":.1f",
                "Latitude": ":.2f", 
                "Longitude": ":.2f",
                "size": False  # Hide size from hover
            },
            color_continuous_scale="Reds",  # Red scale emphasizes danger
            zoom=1,
            height=700,
            mapbox_style="carto-positron",
            title="Earthquake Magnitude Distribution"
        )
        
        # Update layout for better visualization
        fig.update_layout(
            margin={"r":0,"t":50,"l":0,"b":0},
            coloraxis_colorbar=dict(
                title=dict(text="Magnitude", side="right"),
                thickness=15,
                len=0.7,
                x=1.02
            ),
            font=dict(size=12)
        )
        
        # Update traces for better visibility
        fig.update_traces(
            marker=dict(
                opacity=0.7
            )
        )
        
        # Display the map
        st.plotly_chart(fig, use_container_width=True)
        
        # Additional insights
        st.subheader("📈 Magnitude Distribution")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Histogram of magnitudes
            hist_fig = px.histogram(
                filtered_df, 
                x="Magnitude", 
                bins=20,
                title="Frequency by Magnitude",
                color_discrete_sequence=["#ff6b6b"]
            )
            hist_fig.update_layout(height=400)
            st.plotly_chart(hist_fig, use_container_width=True)
        
        with col2:
            # Box plot showing magnitude distribution over time (if date available)
            if 'DateTime' in filtered_df.columns:
                filtered_df['Month'] = filtered_df['DateTime'].dt.to_period('M').astype(str)
                box_fig = px.box(
                    filtered_df, 
                    x="Month", 
                    y="Magnitude",
                    title="Magnitude Distribution Over Time"
                )
                box_fig.update_layout(height=400)
                box_fig.update_xaxis(tickangle=45)
                st.plotly_chart(box_fig, use_container_width=True)
        
        # Show recent high-magnitude earthquakes
        st.subheader("🚨 Highest Magnitude Earthquakes")
        top_earthquakes = filtered_df.nlargest(10, 'Magnitude')[['Magnitude', 'Latitude', 'Longitude']]
        if 'DateTime' in filtered_df.columns:
            top_earthquakes = filtered_df.nlargest(10, 'Magnitude')[['DateTime', 'Magnitude', 'Latitude', 'Longitude']]
        
        st.dataframe(top_earthquakes, use_container_width=True)

except FileNotFoundError:
    st.error("🚫 Could not find 'data/database.csv'. Please make sure the file exists in the correct location.")
    st.info("💡 **Tip**: Make sure your CSV file has columns named 'Latitude', 'Longitude', 'Magnitude', and a date column.")

except Exception as e:
    st.error(f"❌ An error occurred: {str(e)}")
    st.info("Please check your data file format and column names.")
