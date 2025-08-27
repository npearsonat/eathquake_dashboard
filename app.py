import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
import base64
import requests
import time

# Page configuration
st.set_page_config(
    page_title="Global Earthquake Dashboard",
    page_icon="assets/epicenter.png",
    layout="wide"
)

# Background color
st.markdown(
    """
    <style>
    .stApp {
        background-color: white;
        background-image: repeating-linear-gradient(
            45deg,
            #fae4d9,
            #fae4d9 0.5px,
            white 0.5px,
            white 20px
        );
    }
    </style>
    """,
    unsafe_allow_html=True
)

#Image Icons
def get_base64_image(image_path):
    with open(image_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# NEW: USGS API Functions
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_usgs_earthquake_data(magnitude='2.5', timeframe='day'):
    """
    Fetch earthquake data from USGS API
    
    Parameters:
    - magnitude: minimum magnitude ('1.0', '2.5', '4.0', '5.0', '6.0')  
    - timeframe: time period ('hour', 'day', 'week', 'month')
    
    Returns: DataFrame
    """
    
    url = f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{magnitude}_{timeframe}.geojson"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data or 'features' not in data:
            return None, None
            
        features = data['features']
        
        # Extract data into lists
        earthquakes = []
        for feature in features:
            props = feature['properties']
            coords = feature['geometry']['coordinates']
            
            earthquakes.append({
                'Magnitude': props.get('mag'),
                'Place': props.get('place'),
                'DateTime': pd.to_datetime(props.get('time'), unit='ms', utc=True),
                'Latitude': coords[1],
                'Longitude': coords[0],
                'Depth': coords[2],
                'URL': props.get('url'),
                'Felt': props.get('felt'),
                'Tsunami': props.get('tsunami'),
                'Type': props.get('type'),
                'Status': props.get('status'),
                'Updated': pd.to_datetime(props.get('updated'), unit='ms', utc=True) if props.get('updated') else None
            })
        
        df = pd.DataFrame(earthquakes)
        # Remove rows with missing essential data
        df = df.dropna(subset=['Magnitude', 'Latitude', 'Longitude'])
        
        return df, data['metadata']
        
    except Exception as e:
        st.error(f"Error fetching USGS data: {e}")
        return None, None

def create_live_earthquake_map(df, title="Recent Earthquakes"):
    """Create an interactive map for live earthquake data"""
    
    if df.empty:
        return None
    
    # Enhanced size calculation
    base_size = 5
    df_copy = df.copy()
    min_mag = df_copy['Magnitude'].min()
    df_copy["size"] = base_size * (3 ** (df_copy["Magnitude"] - min_mag))
    df_copy["size"] = df_copy["size"].clip(upper=150)
    
    # Create hover text with more information
    df_copy['hover_text'] = df_copy.apply(lambda row: 
        f"<b>Magnitude {row['Magnitude']:.1f}</b><br>" +
        f"{row['Place']}<br>" +
        f"Depth: {row['Depth']:.1f} km<br>" +
        f"Time: {row['DateTime'].strftime('%Y-%m-%d %H:%M:%S UTC')}", 
        axis=1
    )
    
    fig = px.scatter_mapbox(
        df_copy,
        lat="Latitude",       
        lon="Longitude",        
        size="size",
        color="Magnitude",
        hover_name="hover_text",
        color_continuous_scale="Reds",
        zoom=1,
        height=600,
        mapbox_style="carto-positron",
        title=title
    )
    
    fig.update_layout(
        margin={"r":0,"t":50,"l":0,"b":0},
        coloraxis_colorbar=dict(
            title=dict(text="Magnitude", side="right"),
            thickness=15,
            len=0.7,
            x=1.02
        )
    )
    
    fig.update_traces(marker=dict(opacity=0.8))
    
    return fig

# Load earthquake data (existing function)
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
    import geopandas as gpd
    from shapely.geometry import Point

    # Load Natural Earth country boundaries
    countries = gpd.read_file("data/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp")

    # Convert earthquake DataFrame to GeoDataFrame
    geometry = [Point(xy) for xy in zip(df['Longitude'], df['Latitude'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=countries.crs)

    # Perform spatial join to assign country names and ISO codes
    gdf = gpd.sjoin(
        gdf, 
        countries[['ADMIN', 'ISO_A3', 'geometry']], 
        how='left', 
        predicate='within'
    )

    # Rename columns and drop unnecessary ones
    gdf = gdf.rename(columns={
        'ADMIN': 'Country',
        'ISO_A3': 'ISO_Code'
    }).drop(columns=['index_right'])

    return gdf

# Main title and navigation
icon_base64 = get_base64_image("assets/epicenter.png")
st.markdown(
    f'''
    <h1 style="display: flex; align-items: center; gap: 10px;">
        Global Earthquake Dashboard
        <img src="data:image/png;base64,{icon_base64}" width="32" height="32" alt="icon">
    </h1>
    ''',
    unsafe_allow_html=True
)
st.markdown("""Comprehensive analysis and visualization of seismic activity worldwide<br>
Historical Data: Significant Earthquakes, 1965-2016. Source: https://www.kaggle.com/datasets/usgs/earthquake-database.<br>
Live Data: Real-time earthquake information from USGS Earthquake Hazards Program.""",unsafe_allow_html=True)

# UPDATED PAGE SELECTION with new Live Feed option
page = st.selectbox("**Choose Analysis View:**", 
                   ["Live Feed", "Global Earthquake Map", "Earthquake Occurrence By Country"], 
                   label_visibility="visible")

# NEW: LIVE FEED PAGE
if page == "Live Feed":
    st.header("🔴 Live Earthquake Feed")
    st.markdown("**Real-time earthquake data from the USGS Earthquake Hazards Program. Data updates every few minutes.**")
    
    # Live feed controls
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        live_magnitude = st.selectbox(
            "Minimum Magnitude:",
            options=['1.0', '2.5', '4.0', '5.0', '6.0'],
            index=1,
            key="live_mag"
        )
    
    with col2:
        live_timeframe = st.selectbox(
            "Time Period:",
            options=[('hour', 'Past Hour'), ('day', 'Past Day'), ('week', 'Past Week'), ('month', 'Past Month')],
            format_func=lambda x: x[1],
            index=1,
            key="live_time"
        )
    
    with col3:
        if st.button("🔄 Refresh Data", type="primary"):
            st.cache_data.clear()
            st.rerun()
    
    # Fetch live data
    with st.spinner("Fetching live earthquake data..."):
        live_df, metadata = get_usgs_earthquake_data(
            magnitude=live_magnitude,
            timeframe=live_timeframe[0]
        )
    
    if live_df is not None and not live_df.empty:
        # Display metadata
        if metadata:
            st.info(f"📡 Last updated: {pd.to_datetime(metadata['generated'], unit='ms').strftime('%Y-%m-%d %H:%M:%S UTC')} | "
                   f"API Status: ✅ Active | Total events: {len(live_df)}")
        
        # Live statistics
        st.markdown("### 📊 Live Statistics")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown(f"""
            <div style="padding: 1rem; border: 2px solid #28a745; border-radius: 10px; background-color: #f8fff8; text-align: center;">
                <h3 style="margin: 0; color: #28a745; font-size: 1rem;">Total Events</h3>
                <h2 style="margin: 0; color: #155724;">{len(live_df)}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            latest_mag = live_df.iloc[0]['Magnitude'] if len(live_df) > 0 else 0
            st.markdown(f"""
            <div style="padding: 1rem; border: 2px solid #ffc107; border-radius: 10px; background-color: #fffbf0; text-align: center;">
                <h3 style="margin: 0; color: #ffc107; font-size: 1rem;">Latest Magnitude</h3>
                <h2 style="margin: 0; color: #856404;">{latest_mag:.1f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            max_mag = live_df['Magnitude'].max()
            st.markdown(f"""
            <div style="padding: 1rem; border: 2px solid #dc3545; border-radius: 10px; background-color: #fff5f5; text-align: center;">
                <h3 style="margin: 0; color: #dc3545; font-size: 1rem;">Max Magnitude</h3>
                <h2 style="margin: 0; color: #721c24;">{max_mag:.1f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            major_count = len(live_df[live_df['Magnitude'] >= 5.0])
            st.markdown(f"""
            <div style="padding: 1rem; border: 2px solid #6f42c1; border-radius: 10px; background-color: #f8f7ff; text-align: center;">
                <h3 style="margin: 0; color: #6f42c1; font-size: 1rem;">Major (5.0+)</h3>
                <h2 style="margin: 0; color: #3d1a5b;">{major_count}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            avg_depth = live_df['Depth'].mean()
            st.markdown(f"""
            <div style="padding: 1rem; border: 2px solid #17a2b8; border-radius: 10px; background-color: #f7feff; text-align: center;">
                <h3 style="margin: 0; color: #17a2b8; font-size: 1rem;">Avg Depth (km)</h3>
                <h2 style="margin: 0; color: #0c5460;">{avg_depth:.1f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Live Map", "📈 Recent Trends", "📋 Event List", "⏰ Timeline"])
        
        with tab1:
            # Live earthquake map
            live_map = create_live_earthquake_map(
                live_df, 
                f"Live Earthquakes - Magnitude {live_magnitude}+ ({live_timeframe[1]})"
            )
            if live_map:
                st.plotly_chart(live_map, use_container_width=True)
        
        with tab2:
            # Historical trends comparison
            col1, col2 = st.columns(2)
            
            with col1:
                # Magnitude distribution
                mag_hist = px.histogram(
                    live_df,
                    x='Magnitude',
                    nbins=20,
                    title=f"Magnitude Distribution ({live_timeframe[1]})",
                    color_discrete_sequence=['#dc3545']
                )
                mag_hist.update_layout(height=400)
                st.plotly_chart(mag_hist, use_container_width=True)
            
            with col2:
                # Depth vs Magnitude scatter
                depth_scatter = px.scatter(
                    live_df,
                    x='Depth',
                    y='Magnitude',
                    color='Magnitude',
                    title="Depth vs Magnitude",
                    color_continuous_scale='Reds'
                )
                depth_scatter.update_layout(height=400)
                st.plotly_chart(depth_scatter, use_container_width=True)
            
            # Time series if we have enough data points
            if len(live_df) > 1:
                live_df_sorted = live_df.sort_values('DateTime')
                time_series = px.line(
                    live_df_sorted,
                    x='DateTime',
                    y='Magnitude',
                    title=f"Earthquake Magnitude Over Time ({live_timeframe[1]})",
                    markers=True
                )
                time_series.update_layout(height=400)
                st.plotly_chart(time_series, use_container_width=True)
        
        with tab3:
            # Recent earthquakes table
            st.subheader("📋 Recent Earthquake Events")
            
            # Format the data for display
            display_df = live_df.copy()
            display_df['Time (UTC)'] = display_df['DateTime'].dt.strftime('%Y-%m-%d %H:%M:%S')
            display_df['Coordinates'] = display_df.apply(lambda x: f"{x['Latitude']:.3f}, {x['Longitude']:.3f}", axis=1)
            
            table_df = display_df[['Time (UTC)', 'Magnitude', 'Place', 'Depth', 'Coordinates']].copy()
            table_df = table_df.sort_values('Time (UTC)', ascending=False)
            
            # Style the table
            st.dataframe(
                table_df,
                use_container_width=True,
                height=400
            )
            
            # Download option
            csv = table_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Recent Earthquakes CSV",
                data=csv,
                file_name=f"recent_earthquakes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        
        with tab4:
            # Timeline view
            st.subheader("⏰ Earthquake Timeline")
            
            if len(live_df) > 0:
                # Create a timeline chart
                timeline_df = live_df.sort_values('DateTime').copy()
                timeline_df['Size'] = timeline_df['Magnitude'] ** 2 * 10
                
                timeline_fig = px.scatter(
                    timeline_df,
                    x='DateTime',
                    y='Magnitude',
                    size='Size',
                    color='Depth',
                    hover_data=['Place', 'Depth'],
                    title="Earthquake Timeline",
                    color_continuous_scale='Viridis_r'
                )
                timeline_fig.update_layout(height=500)
                st.plotly_chart(timeline_fig, use_container_width=True)
                
                # Show most recent earthquake details
                latest_eq = live_df.iloc[0]
                st.markdown("### 🔥 Most Recent Earthquake")
                
                recent_col1, recent_col2, recent_col3 = st.columns(3)
                
                with recent_col1:
                    st.metric("Magnitude", f"{latest_eq['Magnitude']:.1f}")
                    st.metric("Depth", f"{latest_eq['Depth']:.1f} km")
                
                with recent_col2:
                    st.metric("Location", latest_eq['Place'][:30] + "..." if len(latest_eq['Place']) > 30 else latest_eq['Place'])
                    st.metric("Time (UTC)", latest_eq['DateTime'].strftime('%H:%M:%S'))
                
                with recent_col3:
                    st.metric("Coordinates", f"{latest_eq['Latitude']:.3f}, {latest_eq['Longitude']:.3f}")
                    if latest_eq['URL']:
                        st.markdown(f"[📊 View USGS Details]({latest_eq['URL']})")
    
    else:
        st.warning("⚠️ No recent earthquakes found for the selected criteria, or unable to connect to USGS API.")
        st.info("💡 Try selecting a lower magnitude threshold or check your internet connection.")

# EXISTING PAGES (unchanged)
else:
    try:
        df = load_data()
        
        if not df.empty and 'DateTime' in df.columns:
            min_year = int(df['DateTime'].dt.year.min())
            max_year = int(df['DateTime'].dt.year.max())
            
            year_range = st.sidebar.slider(
                "Select year range:",
                min_value=min_year,
                max_value=max_year,
                value=(min_year, max_year),
                step=1
            )
            start_year, end_year = year_range
        
        if page == "Global Earthquake Map":
            # Title and description
            st.header("Global Analysis")
            st.markdown("**Visualization of earthquake activity worldwide. Shows earthquake epicenter locations.Higher magnitude quakes represented by larger and darker circles**")
            
            # Magnitude filter
            st.sidebar.subheader("Magnitude Range")
            min_mag = float(df['Magnitude'].min())
            max_mag = float(df['Magnitude'].max())
            
            magnitude_range = st.sidebar.slider(
                "Minimum magnitude to display:",
                min_value=min_mag,
                max_value=max_mag,
                value=min_mag,
                step=0.5,
                help="Higher magnitudes represent exponentially more powerful earthquakes"
            )
            
            # Filter data based on selections
            if 'DateTime' in df.columns:
                mask = (
                    (df['DateTime'].dt.year >= start_year) & 
                    (df['DateTime'].dt.year <= end_year) &
                    (df['Magnitude'] >= magnitude_range)
                )
                filtered_df = df[mask].copy()
            else:
                filtered_df = df[df['Magnitude'] >= magnitude_range].copy()
            
            # Display statistics in boxes
            st.markdown("### Summary Statistics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                with st.container():
                    st.markdown("""
                    <div style="padding: 1rem; border: 2px solid #ff6b6b; border-radius: 10px; background-color: #fff5f5; height: 120px; display: flex; flex-direction: column; justify-content: center;">
                        <h3 style="margin: 0; color: #ff6b6b; font-size: 1rem; text-align: center;">Total Earthquakes</h3>
                        <h2 style="margin: 0; color: #d63384; text-align: center;">{}</h2>
                    </div>
                    """.format(len(filtered_df)), unsafe_allow_html=True)
            
            with col2:
                max_mag = f"{filtered_df['Magnitude'].max():.1f}" if not filtered_df.empty else "N/A"
                with st.container():
                    st.markdown("""
                    <div style="padding: 1rem; border: 2px solid #ff6b6b; border-radius: 10px; background-color: #fff5f5; height: 120px; display: flex; flex-direction: column; justify-content: center;">
                        <h3 style="margin: 0; color: #ff6b6b; font-size: 1rem; text-align: center;">Max Magnitude</h3>
                        <h2 style="margin: 0; color: #d63384; text-align: center;">{}</h2>
                    </div>
                    """.format(max_mag), unsafe_allow_html=True)
            
            with col3:
                avg_mag = f"{filtered_df['Magnitude'].mean():.1f}" if not filtered_df.empty else "N/A"
                with st.container():
                    st.markdown("""
                    <div style="padding: 1rem; border: 2px solid #ff6b6b; border-radius: 10px; background-color: #fff5f5; height: 120px; display: flex; flex-direction: column; justify-content: center;">
                        <h3 style="margin: 0; color: #ff6b6b; font-size: 1rem; text-align: center;">Avg Magnitude</h3>
                        <h2 style="margin: 0; color: #d63384; text-align: center;">{}</h2>
                    </div>
                    """.format(avg_mag), unsafe_allow_html=True)
            
            with col4:
                major_earthquakes = len(filtered_df[filtered_df['Magnitude'] >= 7.0])
                with st.container():
                    st.markdown("""
                    <div style="padding: 1rem; border: 2px solid #ff6b6b; border-radius: 10px; background-color: #fff5f5; height: 120px; display: flex; flex-direction: column; justify-content: center;">
                        <h3 style="margin: 0; color: #ff6b6b; font-size: 1rem; text-align: center;">Major Quakes (7.0+)</h3>
                        <h2 style="margin: 0; color: #d63384; text-align: center;">{}</h2>
                    </div>
                    """.format(major_earthquakes), unsafe_allow_html=True)
            
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
                st.subheader("Magnitude Distribution")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Histogram of magnitudes
                    hist_fig = px.histogram(
                        filtered_df, 
                        x="Magnitude", 
                        nbins=20,
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
                            title="Magnitude Distribution Over Time",
                            color_discrete_sequence=['#ff6b6b']
                        )
                        box_fig.update_layout(height=400)
                        box_fig.update_layout(xaxis_tickangle=45)
                        st.plotly_chart(box_fig, use_container_width=True)
        
        elif page == "Earthquake Occurrence By Country":
            st.header("Earthquake Analysis by Country")
            st.markdown("**Country-level earthquake frequency and magnitude analysis. Quake location attributed using epicenter coordinates**")
            
            # Assign countries to earthquakes
            df_with_countries = assign_countries(df)
            
            # Magnitude threshold slider starting at 5.0
            st.sidebar.subheader("Magnitude Range")
            min_magnitude = st.sidebar.slider(
                "Minimum magnitude to display:",
                min_value= 5.0,
                max_value=9.0,
                value=5.0,
                step=0.5,
                help="Higher magnitudes represent exponentially more powerful earthquakes"
            )
            
            # Filter by year range and magnitude
            if 'DateTime' in df_with_countries.columns:
                # Filter by date and magnitude
                country_mask = (
                    (df_with_countries['DateTime'].dt.year >= start_year) & 
                    (df_with_countries['DateTime'].dt.year <= end_year) &
                    (df_with_countries['Magnitude'] >= min_magnitude) &
                    (df_with_countries['Country'].notna())
                )
                country_filtered_df = df_with_countries[country_mask]
            else:
                country_filtered_df = df_with_countries[
                    (df_with_countries['Magnitude'] >= min_magnitude) &
                    (df_with_countries['Country'].notna())
                ]
            
            if country_filtered_df.empty:
                st.warning("No earthquakes found for the selected criteria in known countries.")
            else:
                # SINGLE CALCULATION FOR COUNTRY STATS - This is the fix!
                country_stats = country_filtered_df.groupby(['ISO_Code', 'Country']).agg({
                    'Magnitude': ['count', 'mean', 'max', 'std'],
                    'Latitude': 'first',  # For approximate country position
                    'Longitude': 'first'
                }).round(2)
                
                # Flatten column names
                country_stats.columns = ['Count', 'Avg_Magnitude', 'Max_Magnitude', 'Std_Magnitude', 'Latitude', 'Longitude']
                country_stats = country_stats.reset_index()
                
                # Calculate risk score (combination of frequency and magnitude)
                country_stats['Risk_Score'] = (
                    country_stats['Count'] * 0.3 + 
                    country_stats['Avg_Magnitude'] * 10 + 
                    country_stats['Max_Magnitude'] * 5
                )

                # Display top-level metrics in styled boxes
                st.markdown("### Country Analysis Summary")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    with st.container():
                        st.markdown("""
                        <div style="padding: 1rem; border: 2px solid #ff6b6b; border-radius: 10px; background-color: #fff5f5; height: 120px; display: flex; flex-direction: column; justify-content: center;">
                            <h3 style="margin: 0; color: #ff6b6b; font-size: 1rem; text-align: center;">Countries Analyzed</h3>
                            <h2 style="margin: 0; color: #d63384; text-align: center;">{}</h2>
                        </div>
                        """.format(len(country_stats)), unsafe_allow_html=True)
                
                with col2:
                    top_country = country_stats.loc[country_stats['Count'].idxmax(), 'Country']
                    top_count = country_stats['Count'].max()
                    with st.container():
                        st.markdown("""
                        <div style="padding: 1rem; border: 2px solid #ff6b6b; border-radius: 10px; background-color: #fff5f5; height: 120px; display: flex; flex-direction: column; justify-content: center;">
                            <h3 style="margin: 0; color: #ff6b6b; font-size: 1rem; text-align: center;">Most Active</h3>
                            <h2 style="margin: 0; color: #d63384; font-size: 1rem; text-align: center;">{} ({})</h2>
                        </div>
                        """.format(top_country, top_count), unsafe_allow_html=True)
                
                with col3:
                    highest_mag_country = country_stats.loc[country_stats['Max_Magnitude'].idxmax(), 'Country']
                    highest_mag = country_stats['Max_Magnitude'].max()
                    with st.container():
                        st.markdown("""
                        <div style="padding: 1rem; border: 2px solid #ff6b6b; border-radius: 10px; background-color: #fff5f5; height: 120px; display: flex; flex-direction: column; justify-content: center;">
                            <h3 style="margin: 0; color: #ff6b6b; font-size: 1rem; text-align: center;">Highest Magnitude</h3>
                            <h2 style="margin: 0; color: #d63384; font-size: 1rem; text-align: center;">{} ({})</h2>
                        </div>
                        """.format(highest_mag, highest_mag_country), unsafe_allow_html=True)
                
                with col4:
                    highest_risk_country = country_stats.loc[country_stats['Risk_Score'].idxmax(), 'Country']
                    with st.container():
                        st.markdown("""
                        <div style="padding: 1rem; border: 2px solid #ff6b6b; border-radius: 10px; background-color: #fff5f5; height: 120px; display: flex; flex-direction: column; justify-content: center;">
                            <h3 style="margin: 0; color: #ff6b6b; font-size: 1rem; text-align: center;">Highest Risk</h3>
                            <h2 style="margin: 0; color: #d63384; text-align: center;">{}</h2>
                        </div>
                        """.format(highest_risk_country), unsafe_allow_html=True)
                
                # Create tabs for additional analysis
                tab1, tab2, tab3 = st.tabs(["Country Frequency Map", "Rankings", "Detailed Analysis"])
                
                with tab1:
                    # Choropleth map showing earthquake frequency by country with improved styling
                    choropleth_fig = px.choropleth(
                        country_stats,
                        locations='ISO_Code',
                        color='Count',
                        hover_name='Country',
                        hover_data={
                            'Count': True,
                            'Avg_Magnitude': ':.1f',
                            'Max_Magnitude': ':.1f',
                            'ISO_Code': False
                        },
                        color_continuous_scale='Reds',
                        title=f"Earthquake Frequency by Country (Magnitude {min_magnitude:.1f}+)",
                        labels={'Count': 'Number of Earthquakes'}
                    )

                    choropleth_fig.add_trace(go.Scattergeo(
                        locations=country_stats['ISO_Code'],
                        locationmode='ISO-3',
                        text=country_stats['Count'],
                        mode='text',
                        textfont=dict(color='black', size=10),
                        showlegend=False
                    ))
                    
                    # Update layout with similar styling to first page
                    choropleth_fig.update_layout(
                        height=700,
                        margin={"r":0,"t":50,"l":0,"b":0},
                        geo=dict(
                            showframe=False, 
                            showcoastlines=True,
                            bgcolor='rgba(0,0,0,0)',
                            lakecolor='lightblue',
                            landcolor='lightgray',
                            coastlinecolor='darkgray'
                        ),
                        coloraxis_colorbar=dict(
                            title=dict(text="Earthquake Count", side="right"),
                            thickness=15,
                            len=0.7,
                            x=1.02
                        ),
                        font=dict(size=12)
                    )
                    
                    st.plotly_chart(choropleth_fig, use_container_width=True)
                
                with tab2:
                    # Rankings and statistics
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Top 10 by Frequency")
                        top_frequency = country_stats.nlargest(10, 'Count')[['Country', 'Count', 'Avg_Magnitude']]
                        st.dataframe(top_frequency, use_container_width=True)
                        
                        # Bar chart of top countries by frequency
                        freq_fig = px.bar(
                            top_frequency,
                            x='Country',
                            y='Count',
                            title="Top Countries by Earthquake Frequency",
                            color='Count',
                            color_continuous_scale='Reds'
                        )
                        freq_fig.update_layout(xaxis_tickangle=45, height=400)
                        st.plotly_chart(freq_fig, use_container_width=True)
                    
                    with col2:
                        st.subheader("Top 10 by Max Magnitude")
                        top_magnitude = country_stats.nlargest(10, 'Max_Magnitude')[['Country', 'Max_Magnitude', 'Count']]
                        st.dataframe(top_magnitude, use_container_width=True)
                        
                        # Bar chart of top countries by magnitude
                        mag_fig = px.bar(
                            top_magnitude,
                            x='Country',
                            y='Max_Magnitude',
                            title="Top Countries by Maximum Magnitude",
                            color='Max_Magnitude',
                            color_continuous_scale='Reds'
                        )
                        mag_fig.update_layout(xaxis_tickangle=45, height=400)
                        st.plotly_chart(mag_fig, use_container_width=True)
                
                with tab3:
                    # Detailed analysis
                    st.subheader("Risk Assessment")
                    
                    # Scatter plot: Frequency vs Average Magnitude
                    risk_fig = px.scatter(
                        country_stats,
                        x='Count',
                        y='Avg_Magnitude',
                        size='Max_Magnitude',
                        color='Risk_Score',
                        hover_name='Country',
                        title="Earthquake Risk Assessment: Frequency vs Average Magnitude",
                        labels={
                            'Count': 'Number of Earthquakes',
                            'Avg_Magnitude': 'Average Magnitude',
                            'Risk_Score': 'Risk Score'
                        },
                        color_continuous_scale='Reds'
                    )
                    risk_fig.update_layout(height=500)
                    st.plotly_chart(risk_fig, use_container_width=True)
                    
                    st.subheader("📋 Complete Country Statistics")
                    display_stats = country_stats[['Country', 'Count', 'Avg_Magnitude', 'Max_Magnitude', 'Risk_Score']].copy()
                    display_stats = display_stats.sort_values('Risk_Score', ascending=False)
                    st.dataframe(display_stats, use_container_width=True)

    except FileNotFoundError:
        st.error("🚫 Could not find 'data/database.csv'. Please make sure the file exists in the correct location.")
        st.info("💡 **Tip**: Make sure your CSV file has columns named 'Latitude', 'Longitude', 'Magnitude', and a date column.")

    except Exception as e:
        st.error(f"❌ An error occurred: {str(e)}")
        st.info("Please check your data file format and column names.")
