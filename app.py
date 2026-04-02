import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests
import geopandas as gpd
from shapely.geometry import Point

# ── App setup ────────────────────────────────────────────────────────────────
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)
server = app.server

# ── Colors / style constants ─────────────────────────────────────────────────
CARD_STYLE = {
    "borderRadius": "12px",
    "boxShadow": "0 2px 8px rgba(0,0,0,0.08)",
    "padding": "1.2rem",
    "background": "#fff",
    "marginBottom": "1rem"
}
STAT_STYLE = {
    "borderRadius": "10px",
    "padding": "1rem",
    "textAlign": "center",
    "background": "#f8f9fa",
    "border": "1px solid #e9ecef"
}

# ── Data loaders ─────────────────────────────────────────────────────────────
def load_historical():
    df = pd.read_csv("data/database.csv")
    for col in ["Date", "date", "DateTime", "datetime", "Time", "time"]:
        if col in df.columns:
            df["DateTime"] = pd.to_datetime(df[col], errors="coerce")
            break
    df = df.dropna(subset=["Latitude", "Longitude", "Magnitude", "DateTime"])
    return df

def assign_countries(df):
    countries = gpd.read_file("data/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp")
    geometry = [Point(xy) for xy in zip(df["Longitude"], df["Latitude"])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=countries.crs)
    gdf = gpd.sjoin(gdf, countries[["ADMIN", "ISO_A3", "geometry"]], how="left", predicate="within")
    return gdf.rename(columns={"ADMIN": "Country", "ISO_A3": "ISO_Code"}).drop(columns=["index_right"])

def fetch_usgs(magnitude="2.5", timeframe="day"):
    url = f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{magnitude}_{timeframe}.geojson"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        rows = []
        for f in data["features"]:
            p, c = f["properties"], f["geometry"]["coordinates"]
            mag = p.get("mag")
            if mag is None or mag < float(magnitude):
                continue
            rows.append({
                "Magnitude": mag,
                "Place": p.get("place"),
                "DateTime": pd.to_datetime(p.get("time"), unit="ms", utc=True),
                "Latitude": c[1], "Longitude": c[0], "Depth": c[2],
                "URL": p.get("url"),
            })
        df = pd.DataFrame(rows).dropna(subset=["Magnitude", "Latitude", "Longitude"])
        return df, data.get("metadata", {})
    except Exception as e:
        print(f"USGS fetch error: {e}")
        return pd.DataFrame(), {}

# Pre-load historical data once
hist_df = load_historical()
hist_min_year = int(hist_df["DateTime"].dt.year.min())
hist_max_year = int(hist_df["DateTime"].dt.year.max())

# ── Sidebar ───────────────────────────────────────────────────────────────────
sidebar = html.Div([
    html.Div([
        html.H4("Earthquake Monitor", className="fw-bold mb-1", style={"color": "#2c3e50"}),
        html.P("Global Seismic Activity", className="text-muted small mb-0"),
    ], style={"padding": "1.5rem 1rem 1rem"}),
    html.Hr(style={"margin": "0 1rem"}),
    dbc.Nav([
        dbc.NavLink("Live Feed", href="/live", active="exact", className="nav-item-custom"),
        dbc.NavLink("Global Map", href="/map", active="exact", className="nav-item-custom"),
        dbc.NavLink("By Country", href="/country", active="exact", className="nav-item-custom"),
    ], vertical=True, pills=True, style={"padding": "0.5rem"}),
], style={
    "position": "fixed", "top": 0, "left": 0, "bottom": 0, "width": "220px",
    "background": "#ffffff", "borderRight": "1px solid #e9ecef",
    "boxShadow": "2px 0 8px rgba(0,0,0,0.06)", "zIndex": 100
})

# ── Page: Live Feed ───────────────────────────────────────────────────────────
live_layout = html.Div([
    html.H3("Live Earthquake Feed", className="fw-bold mb-1"),
    html.P("Real-time data from the USGS Earthquake Hazards Program, refreshed every 5 minutes.", className="text-muted mb-3"),
    dbc.Row([
        dbc.Col(dbc.Select(id="live-mag", options=[
            {"label": "Magnitude 1.0+", "value": "1.0"},
            {"label": "Magnitude 2.5+", "value": "2.5"},
            {"label": "Magnitude 4.5+", "value": "4.5"},
        ], value="2.5"), md=3),
        dbc.Col(dbc.Select(id="live-time", options=[
            {"label": "Past Hour", "value": "hour"},
            {"label": "Past Day", "value": "day"},
            {"label": "Past Week", "value": "week"},
            {"label": "Past Month", "value": "month"},
        ], value="day"), md=3),
        dbc.Col(dbc.Button("🔄 Refresh", id="live-refresh", color="primary", outline=True), md=2),
    ], className="mb-3 g-2"),
    html.Div(id="live-stats", className="mb-3"),
    dbc.Tabs([
        dbc.Tab(dcc.Graph(id="live-map"), label="Map"),
        dbc.Tab(html.Div(id="live-trends"), label="Trends"),
        dbc.Tab(html.Div(id="live-table"), label="Event List"),
        dbc.Tab(dcc.Graph(id="live-timeline"), label="Timeline"),
    ]),
    dcc.Interval(id="live-interval", interval=300_000, n_intervals=0),
])

# ── Page: Global Map ──────────────────────────────────────────────────────────
map_layout = html.Div([
    html.H3("Global Earthquake Map", className="fw-bold mb-1"),
    html.P("Historical earthquake data from the NEIC dataset (1965–2016).", className="text-muted mb-3"),
    dbc.Row([
        dbc.Col([
            html.Label("Year Range", className="fw-semibold small"),
            dcc.RangeSlider(id="map-year", min=hist_min_year, max=hist_max_year,
                            value=[hist_min_year, hist_max_year],
                            marks={y: str(y) for y in range(hist_min_year, hist_max_year+1, 10)},
                            tooltip={"placement": "bottom"}),
        ], md=8),
        dbc.Col([
            html.Label("Min Magnitude", className="fw-semibold small"),
            dcc.Slider(id="map-mag", min=5.0, max=9.5, step=0.5, value=5.0,
                       marks={m: str(m) for m in [5, 6, 7, 8, 9]},
                       tooltip={"placement": "bottom"}),
        ], md=4),
    ], className="mb-3 g-3", style={**CARD_STYLE}),
    html.Div(id="map-stats", className="mb-3"),
    dcc.Graph(id="map-globe", style={"height": "600px"}),
    dbc.Row([
        dbc.Col(dcc.Graph(id="map-hist"), md=6),
        dbc.Col(dcc.Graph(id="map-box"), md=6),
    ]),
])

# ── Page: By Country ─────────────────────────────────────────────────────────
country_layout = html.Div([
    html.H3("Earthquakes by Country", className="fw-bold mb-1"),
    html.P("Country-level frequency and magnitude analysis. Epicenters attributed via coordinate lookup.", className="text-muted mb-3"),
    dbc.Row([
        dbc.Col([
            html.Label("Year Range", className="fw-semibold small"),
            dcc.RangeSlider(id="country-year", min=hist_min_year, max=hist_max_year,
                            value=[hist_min_year, hist_max_year],
                            marks={y: str(y) for y in range(hist_min_year, hist_max_year+1, 10)},
                            tooltip={"placement": "bottom"}),
        ], md=8),
        dbc.Col([
            html.Label("Min Magnitude", className="fw-semibold small"),
            dcc.Slider(id="country-mag", min=5.0, max=9.0, step=0.5, value=5.0,
                       marks={m: str(m) for m in [5, 6, 7, 8, 9]},
                       tooltip={"placement": "bottom"}),
        ], md=4),
    ], className="mb-3 g-3", style={**CARD_STYLE}),
    html.Div(id="country-stats", className="mb-3"),
    dbc.Tabs([
        dbc.Tab(dcc.Graph(id="country-choropleth"), label="Frequency Map"),
        dbc.Tab(html.Div(id="country-rankings"), label="Rankings"),
        dbc.Tab(dcc.Graph(id="country-risk"), label="Risk Assessment"),
    ]),
])

# ── App layout ────────────────────────────────────────────────────────────────
app.layout = html.Div([
    dcc.Location(id="url"),
    sidebar,
    html.Div(id="page-content", style={
        "marginLeft": "240px", "padding": "2rem", "minHeight": "100vh",
        "background": "#f8f9fa"
    }),
], style={"fontFamily": "'Inter', sans-serif"})

# ── Routing ───────────────────────────────────────────────────────────────────
@callback(Output("page-content", "children"), Input("url", "pathname"))
def route(path):
    if path == "/map":     return map_layout
    if path == "/country": return country_layout
    return live_layout  # default

# ── Live Feed callbacks ───────────────────────────────────────────────────────
@callback(
    Output("live-stats", "children"),
    Output("live-map", "figure"),
    Output("live-trends", "children"),
    Output("live-table", "children"),
    Output("live-timeline", "figure"),
    Input("live-mag", "value"),
    Input("live-time", "value"),
    Input("live-refresh", "n_clicks"),
    Input("live-interval", "n_intervals"),
)
def update_live(mag, timeframe, _, __):
    df, meta = fetch_usgs(mag, timeframe)
    empty_fig = go.Figure().update_layout(template="simple_white", paper_bgcolor="rgba(0,0,0,0)")

    if df.empty:
        return dbc.Alert("No data returned from USGS. Try different filters.", color="warning"), \
               empty_fig, html.P("No data."), html.P("No data."), empty_fig

    # Stats row
    def stat(label, value):
        return dbc.Col(html.Div([
            html.P(label, className="text-muted small mb-1"),
            html.H4(value, className="fw-bold mb-0", style={"color": "#2c3e50"})
        ], style=STAT_STYLE))

    updated = pd.to_datetime(meta.get("generated"), unit="ms").strftime("%Y-%m-%d %H:%M UTC") if meta.get("generated") else "—"
    stats = dbc.Row([
        stat("Total Events", len(df)),
        stat("Latest Mag", f"{df.iloc[0]['Magnitude']:.1f}"),
        stat("Max Mag", f"{df['Magnitude'].max():.1f}"),
        stat("Major (5.0+)", len(df[df["Magnitude"] >= 5])),
        stat("Avg Depth (km)", f"{df['Depth'].mean():.1f}"),
        dbc.Col(html.Div([
            html.P("Last Updated", className="text-muted small mb-1"),
            html.P(updated, className="small mb-0 fw-semibold")
        ], style=STAT_STYLE)),
    ], className="g-2", style={**CARD_STYLE})

    # Map
    df2 = df.copy()
    df2["size"] = (5 * (3 ** (df2["Magnitude"] - df2["Magnitude"].min()))).clip(upper=150)
    map_fig = px.scatter_mapbox(df2, lat="Latitude", lon="Longitude", size="size",
                                color="Magnitude", hover_name="Place",
                                hover_data={"Depth": True, "size": False},
                                color_continuous_scale="Reds", zoom=1, height=550,
                                mapbox_style="carto-positron")
    map_fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    # Trends
    h1 = px.histogram(df, x="Magnitude", nbins=20, title="Magnitude Distribution",
                      color_discrete_sequence=["#e74c3c"])
    h1.update_layout(height=380, template="simple_white")
    h2 = px.scatter(df, x="Depth", y="Magnitude", color="Magnitude",
                    title="Depth vs Magnitude", color_continuous_scale="Reds")
    h2.update_layout(height=380, template="simple_white")
    trends = dbc.Row([dbc.Col(dcc.Graph(figure=h1), md=6), dbc.Col(dcc.Graph(figure=h2), md=6)])

    # Table
    tdf = df[["DateTime", "Magnitude", "Place", "Depth", "Latitude", "Longitude"]].copy()
    tdf["DateTime"] = tdf["DateTime"].dt.strftime("%Y-%m-%d %H:%M UTC")
    tdf = tdf.sort_values("DateTime", ascending=False)
    table = dbc.Table.from_dataframe(tdf.head(50), striped=True, bordered=False,
                                     hover=True, responsive=True, size="sm",
                                     className="small")

    # Timeline
    tl = df.sort_values("DateTime").copy()
    tl["size"] = tl["Magnitude"] ** 2 * 10
    tl_fig = px.scatter(tl, x="DateTime", y="Magnitude", size="size", color="Depth",
                        hover_data=["Place"], title="Earthquake Timeline",
                        color_continuous_scale="Viridis_r")
    tl_fig.update_layout(height=450, template="simple_white")

    return stats, map_fig, trends, table, tl_fig

# ── Global Map callbacks ──────────────────────────────────────────────────────
@callback(
    Output("map-stats", "children"),
    Output("map-globe", "figure"),
    Output("map-hist", "figure"),
    Output("map-box", "figure"),
    Input("map-year", "value"),
    Input("map-mag", "value"),
)
def update_map(yr, mag):
    df = hist_df.copy()
    mask = (df["DateTime"].dt.year >= yr[0]) & (df["DateTime"].dt.year <= yr[1]) & (df["Magnitude"] >= mag)
    fdf = df[mask]
    empty = go.Figure().update_layout(template="simple_white")
    if fdf.empty:
        return dbc.Alert("No data for selected filters.", color="warning"), empty, empty, empty

    def stat(label, value):
        return dbc.Col(html.Div([
            html.P(label, className="text-muted small mb-1"),
            html.H4(value, className="fw-bold mb-0", style={"color": "#2c3e50"})
        ], style=STAT_STYLE))

    stats = dbc.Row([
        stat("Total", f"{len(fdf):,}"),
        stat("Max Mag", f"{fdf['Magnitude'].max():.1f}"),
        stat("Avg Mag", f"{fdf['Magnitude'].mean():.1f}"),
        stat("Major (7.0+)", len(fdf[fdf["Magnitude"] >= 7])),
    ], className="g-2", style={**CARD_STYLE})

    fdf2 = fdf.copy()
    fdf2["size"] = (3 * (3 ** (fdf2["Magnitude"] - fdf2["Magnitude"].min()))).clip(upper=100)
    globe = px.scatter_mapbox(fdf2, lat="Latitude", lon="Longitude", size="size",
                              color="Magnitude", hover_data={"Magnitude": ":.1f", "size": False},
                              color_continuous_scale="Reds", zoom=1, height=580,
                              mapbox_style="carto-positron")
    globe.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    hist_fig = px.histogram(fdf, x="Magnitude", nbins=20, title="Frequency by Magnitude",
                            color_discrete_sequence=["#e74c3c"])
    hist_fig.update_layout(height=380, template="simple_white")

    fdf3 = fdf.copy()
    fdf3["Year"] = fdf3["DateTime"].dt.year
    box_fig = px.box(fdf3, x="Year", y="Magnitude", title="Magnitude by Year",
                     color_discrete_sequence=["#e74c3c"])
    box_fig.update_layout(height=380, template="simple_white", xaxis_tickangle=45)

    return stats, globe, hist_fig, box_fig

# ── Country callbacks ─────────────────────────────────────────────────────────
@callback(
    Output("country-stats", "children"),
    Output("country-choropleth", "figure"),
    Output("country-rankings", "children"),
    Output("country-risk", "figure"),
    Input("country-year", "value"),
    Input("country-mag", "value"),
)
def update_country(yr, mag):
    df = assign_countries(hist_df.copy())
    mask = (
        (df["DateTime"].dt.year >= yr[0]) & (df["DateTime"].dt.year <= yr[1]) &
        (df["Magnitude"] >= mag) & df["Country"].notna()
    )
    fdf = df[mask]
    empty = go.Figure().update_layout(template="simple_white")
    if fdf.empty:
        return dbc.Alert("No data for selected filters.", color="warning"), empty, html.P("No data."), empty

    cs = fdf.groupby(["ISO_Code", "Country"]).agg(
        Count=("Magnitude", "count"),
        Avg_Mag=("Magnitude", "mean"),
        Max_Mag=("Magnitude", "max"),
    ).round(2).reset_index()
    cs["Risk"] = (cs["Count"] * 0.3 + cs["Avg_Mag"] * 10 + cs["Max_Mag"] * 5).round(1)

    def stat(label, value):
        return dbc.Col(html.Div([
            html.P(label, className="text-muted small mb-1"),
            html.H4(str(value), className="fw-bold mb-0", style={"color": "#2c3e50"})
        ], style=STAT_STYLE))

    stats = dbc.Row([
        stat("Countries", len(cs)),
        stat("Most Active", cs.loc[cs["Count"].idxmax(), "Country"]),
        stat("Highest Mag", f"{cs['Max_Mag'].max():.1f} — {cs.loc[cs['Max_Mag'].idxmax(),'Country']}"),
        stat("Highest Risk", cs.loc[cs["Risk"].idxmax(), "Country"]),
    ], className="g-2", style={**CARD_STYLE})

    choro = px.choropleth(cs, locations="ISO_Code", color="Count", hover_name="Country",
                          hover_data={"Avg_Mag": ":.1f", "Max_Mag": ":.1f", "ISO_Code": False},
                          color_continuous_scale="Reds",
                          title=f"Earthquake Frequency by Country (Mag {mag}+)")
    choro.update_layout(height=600, margin={"r":0,"t":50,"l":0,"b":0},
                        geo=dict(showframe=False, showcoastlines=True,
                                 bgcolor="rgba(0,0,0,0)", landcolor="#f0f0f0"))

    # Rankings
    top_freq = cs.nlargest(10, "Count")[["Country", "Count", "Avg_Mag"]]
    top_mag  = cs.nlargest(10, "Max_Mag")[["Country", "Max_Mag", "Count"]]
    b1 = px.bar(top_freq, x="Country", y="Count", title="Top 10 by Frequency",
                color="Count", color_continuous_scale="Reds")
    b1.update_layout(height=400, template="simple_white", xaxis_tickangle=45, showlegend=False)
    b2 = px.bar(top_mag, x="Country", y="Max_Mag", title="Top 10 by Max Magnitude",
                color="Max_Mag", color_continuous_scale="Reds")
    b2.update_layout(height=400, template="simple_white", xaxis_tickangle=45, showlegend=False)
    rankings = dbc.Row([dbc.Col(dcc.Graph(figure=b1), md=6), dbc.Col(dcc.Graph(figure=b2), md=6)])

    risk_fig = px.scatter(cs, x="Count", y="Avg_Mag", size="Max_Mag", color="Risk",
                          hover_name="Country", title="Risk: Frequency vs Avg Magnitude",
                          color_continuous_scale="Reds")
    risk_fig.update_layout(height=500, template="simple_white")

    return stats, choro, rankings, risk_fig

if __name__ == "__main__":
    app.run(debug=True)
