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

# Navigation - MOVED TO TOP LEVEL
page = st.sidebar.selectbox("Choose Page", ["🌍 Global Map", "🗺️ By Country"])

try:
    df = load_data()
    
    if page == "🌍 Global Map":
        # Title and description
        st.title("🌍 Global Earthquake Dashboard")
        st.markdown("**Real-time visualization of earthquake activity worldwide**")
        
        # Sidebar controls
        st.sidebar.header(" Controls")
        
        # Time range slider
        if not df.empty and 'DateTime' in df.columns:
            min_date = df['DateTime'].min().date()
            max_date = df['DateTime'].max().date()
            
            st.sidebar.subheader("Time Range")
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
        st.sidebar.subheader("Magnitude Range")
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
    
    elif page == "🗺️ By Country":
        st.title("🗺️ Earthquake Analysis by Country")
        st.markdown("**Country-level earthquake frequency and magnitude analysis**")
        
        # Assign countries to earthquakes
        df_with_countries = assign_countries(df)
        
        # Sidebar controls for country analysis
        st.sidebar.header("🎛️ Country Analysis Controls")
        
        # Magnitude threshold for analysis
        st.sidebar.subheader("📊 Magnitude Categories")
        magnitude_categories = {
            "All Earthquakes": 0.0,
            "Minor (4.0+)": 4.0,
            "Light (5.0+)": 5.0,
            "Moderate (6.0+)": 6.0,
            "Strong (7.0+)": 7.0,
            "Major (8.0+)": 8.0
        }
        
        selected_category = st.sidebar.selectbox(
            "Select earthquake category:",
            list(magnitude_categories.keys()),
            index=2,  # Default to "Light (5.0+)"
            help="Higher magnitude thresholds show only more significant earthquakes"
        )
        
        min_magnitude = magnitude_categories[selected_category]
        
        # Time range for country analysis
        if 'DateTime' in df_with_countries.columns:
            min_date = df_with_countries['DateTime'].min().date()
            max_date = df_with_countries['DateTime'].max().date()
            
            st.sidebar.subheader("📅 Time Range")
            country_date_range = st.sidebar.date_input(
                "Select date range for analysis:",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="country_date_range"
            )
            
            # Handle single date selection
            if isinstance(country_date_range, tuple) and len(country_date_range) == 2:
                country_start_date, country_end_date = country_date_range
            else:
                country_start_date = country_end_date = country_date_range
            
            # Filter by date and magnitude
            country_mask = (
                (df_with_countries['DateTime'].dt.date >= country_start_date) & 
                (df_with_countries['DateTime'].dt.date <= country_end_date) &
                (df_with_countries['Magnitude'] >= min_magnitude) &
                (df_with_countries['Country'] != 'Unknown')
            )
            country_filtered_df = df_with_countries[country_mask]
        else:
            country_filtered_df = df_with_countries[
                (df_with_countries['Magnitude'] >= min_magnitude) &
                (df_with_countries['Country'] != 'Unknown')
            ]
        
        if country_filtered_df.empty:
            st.warning("No earthquakes found for the selected criteria in known countries.")
        else:
            # Calculate country statistics
            country_stats = country_filtered_df.groupby('Country').agg({
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
            
            # Display top-level metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Countries Analyzed", len(country_stats))
            
            with col2:
                top_country = country_stats.loc[country_stats['Count'].idxmax(), 'Country']
                top_count = country_stats['Count'].max()
                st.metric("Most Active Country", f"{top_country} ({top_count})")
            
            with col3:
                highest_mag_country = country_stats.loc[country_stats['Max_Magnitude'].idxmax(), 'Country']
                highest_mag = country_stats['Max_Magnitude'].max()
                st.metric("Highest Magnitude", f"{highest_mag} ({highest_mag_country})")
            
            with col4:
                highest_risk_country = country_stats.loc[country_stats['Risk_Score'].idxmax(), 'Country']
                st.metric("Highest Risk Country", highest_risk_country)
            
            # Create choropleth map
            # Map country names to ISO codes for choropleth
            country_iso_mapping = {
                'United States': 'USA', 'Japan': 'JPN', 'Indonesia': 'IDN', 
                'Chile': 'CHL', 'Mexico': 'MEX', 'Turkey': 'TUR', 'Iran': 'IRN',
                'Peru': 'PER', 'Greece': 'GRC', 'Italy': 'ITA', 'Philippines': 'PHL',
                'New Zealand': 'NZL', 'China': 'CHN', 'India': 'IND', 
                'Afghanistan': 'AFG', 'Russia': 'RUS', 'Papua New Guinea': 'PNG',
                'Ecuador': 'ECU', 'Guatemala': 'GTM', 'Costa Rica': 'CRI'
            }
            
            country_stats['ISO_Code'] = country_stats['Country'].map(country_iso_mapping)
            
            # Create tabs for different visualizations
            tab1, tab2, tab3 = st.tabs(["🗺️ Country Frequency Map", "📊 Rankings", "📈 Detailed Analysis"])
            
            with tab1:
                # Choropleth map showing earthquake frequency by country
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
                    title=f"Earthquake Frequency by Country ({selected_category})",
                    labels={'Count': 'Number of Earthquakes'}
                )
                
                choropleth_fig.update_layout(
                    height=600,
                    geo=dict(showframe=False, showcoastlines=True)
                )
                
                st.plotly_chart(choropleth_fig, use_container_width=True)
            
            with tab2:
                # Rankings and statistics
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🏆 Top 10 by Frequency")
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
                    st.subheader("⚡ Top 10 by Max Magnitude")
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
                st.subheader("📈 Risk Assessment")
                
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
                
                # Complete country statistics table
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
