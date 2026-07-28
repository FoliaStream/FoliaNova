import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import pydeck as pdk
import numpy as np

import os
import yaml
import folium

from streamlit_plotly_events import plotly_events
from streamlit_folium import folium_static, st_folium

from src.functions_fe.sidebar import setup_sidebar
from src.functions_fe.styles import HIDE_SIDEBAR_NAV
from src.functions_fe.country_names_convert import country_name_to_alpha3
from src.functions_fe.load_regions import load_regions
from pipe.functions.functions_I import source_import_api
from pipe.functions.functions_II import hectares_to_circle_radius
from pipe.streamain import main


################
# --- SET UP ---
################

# --- PAGE CONFIG ---
st.set_page_config(page_title="FoliaNova - SIMULATOR", layout="wide")

# --- STYLES ---
st.markdown(HIDE_SIDEBAR_NAV, unsafe_allow_html=True)

# --- CONFIG ---
with open(f"{os.getcwd()}/src/config_fe/config.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)

# --- SIDEBAR & TITLE ---
selected_page = setup_sidebar(
    pages=config['pages'],
    main_page=config['main_page']
)

# Navigation on click
if selected_page == "HOME":
    st.switch_page("HOME.py")
elif selected_page == "SIMULATOR":
    pass
elif selected_page == "OVERVIEW":
    st.switch_page("pages/OVERVIEW.py")

# -- HEADER ---
st.title("🌱 SIMULATOR")


##########################
# --- STATIC RESOURCES ---
##########################

highlighted_countries_names = config['countries']
highlighted_countries_codes = [country_name_to_alpha3(country) for country in config['countries']]

SECTOR_OPTIONS = [
    'Select sector',
    "electricity-generation", "cement", "aluminum", "pulp-and-paper",
    "chemicals", "oil-and-gas-refining", "coal-mining", "bauxite-mining",
    "iron-mining", "copper-mining"
]

# Colors
HIGHLIGHT_COLOR = "rgba(0, 255, 0, 0.5)"
BORDER_COLOR = "rgb(0, 80, 200)"
BACKGROUND_COLOR = "rgb(245, 248, 250)"
OCEAN_COLOR = "rgb(220, 235, 255)"
PLANT_COLOR = "rgb(255, 140, 0)"
RESULT_CIRCLE_COLOR = "rgb(120, 0, 200)"

# Hover texts for the world view
hover_texts = []
for country in highlighted_countries_names:
    hover_texts.append(f"<span style='font-size: 20px;'>{country}</span><b></b><br>")


##########################
# --- SESSION STATE -----
##########################

if "view" not in st.session_state:
    st.session_state.view = "world"          # "world" or "country"
if "selected_country" not in st.session_state:
    st.session_state.selected_country = None
if "selected_region" not in st.session_state:
    st.session_state.selected_region = None
if "selected_site" not in st.session_state:
    st.session_state.selected_site = None          # a single plant name, mutually exclusive with selected_region
if "selected_sector" not in st.session_state:
    st.session_state.selected_sector = 'Select sector'
if "result_circle" not in st.session_state:
    st.session_state.result_circle = None          # dict: center_lon, center_lat, radius_deg, label — set after RUN
if "df_result" not in st.session_state:
    st.session_state.df_result = None


##########################
# --- FIGURE BUILDERS ---
##########################

def min_pairwise_distance(regions_lon, regions_lat):
    """
    Smallest angular distance between any two regions (longitude compressed
    by cos(latitude) so it approximates real ground distance). Used to make
    sure the closest two region labels don't overlap, independent of how
    large the country is overall.
    """
    n = len(regions_lon)
    if n < 2:
        return None

    mean_lat = np.mean(regions_lat)
    cos_lat = np.cos(np.radians(mean_lat))

    min_dist = np.inf
    for i in range(n):
        for j in range(i + 1, n):
            dlon = (regions_lon[i] - regions_lon[j]) * cos_lat
            dlat = regions_lat[i] - regions_lat[j]
            dist = np.sqrt(dlon ** 2 + dlat ** 2)
            if dist < min_dist:
                min_dist = dist

    return min_dist


def compute_zoom_scale(regions_lon, regions_lat, min_scale=1.3, max_scale=9.0, padding=1.3):
    """
    Derives an orthographic 'scale' value from two competing constraints:

    1. FIT: the whole country's region spread should stay on screen
       (large bounding box -> zoom out).
    2. SEPARATE: the two closest regions should stay far enough apart that
       their text labels don't overlap (tightly clustered regions -> zoom in).

    We take whichever constraint asks for MORE zoom (the larger of the two
    scales), then clamp to [min_scale, max_scale] so it never goes absurdly
    far in either direction.
    """
    if not regions_lon or not regions_lat or len(regions_lon) < 2:
        return 4.0

    lon_span = max(regions_lon) - min(regions_lon)
    lat_span = max(regions_lat) - min(regions_lat)
    mean_lat = np.mean(regions_lat)
    lon_span_adjusted = lon_span * np.cos(np.radians(mean_lat))

    fit_span = max(lon_span_adjusted, lat_span, 0.5) * padding
    scale_fit = 40.0 / fit_span

    nn_dist = min_pairwise_distance(regions_lon, regions_lat)
    scale_separate = (6.0 / nn_dist) if nn_dist and nn_dist > 0 else scale_fit

    scale = max(scale_fit, scale_separate)
    return float(np.clip(scale, min_scale, max_scale))


def region_label_fontsize(n_regions, base_size=13, min_size=8):
    """Shrinks label text as region count grows, to ease crowding further."""
    size = base_size - (n_regions // 6)
    return max(size, min_size)


def filter_valid_coordinates(names, lons, lats):
    """
    Drops any region whose lon/lat isn't a finite real number (NaN, inf, or
    missing/None from source data). Keeps the three lists aligned by index.
    """
    clean_names, clean_lons, clean_lats = [], [], []
    dropped = []

    for name, lon, lat in zip(names, lons, lats):
        try:
            lon_f, lat_f = float(lon), float(lat)
        except (TypeError, ValueError):
            dropped.append(name)
            continue

        if np.isfinite(lon_f) and np.isfinite(lat_f):
            clean_names.append(name)
            clean_lons.append(lon_f)
            clean_lats.append(lat_f)
        else:
            dropped.append(name)

    return clean_names, clean_lons, clean_lats, dropped


def generate_circle_coords(center_lon, center_lat, radius_deg, n_points=48):
    """
    Generates an approximate circle (in lon/lat degrees) around a centroid.
    Longitude is compressed by cos(latitude) so the circle looks round on
    the globe rather than stretched near the poles.
    """
    cos_lat = np.cos(np.radians(center_lat))
    cos_lat = cos_lat if abs(cos_lat) > 1e-6 else 1e-6  # avoid divide-by-zero near the poles

    thetas = np.linspace(0, 2 * np.pi, n_points)
    lons = center_lon + (radius_deg / cos_lat) * np.cos(thetas)
    lats = center_lat + radius_deg * np.sin(thetas)
    return lons.tolist(), lats.tolist()


def build_region_circle_traces_data(regions_lon, regions_lat, min_radius=0.15, max_radius=2.5,
                                     shrink_factor=0.4):
    """
    Builds one combined lon/lat line array (with None gaps) containing a
    circle around every region's centroid, sized from that region's
    distance to its nearest neighbor so dense clusters don't overlap.
    """
    n = len(regions_lon)
    all_lons, all_lats = [], []

    for i in range(n):
        if n > 1:
            cos_lat = np.cos(np.radians(regions_lat[i]))
            nearest = min(
                np.sqrt(((regions_lon[i] - regions_lon[j]) * cos_lat) ** 2 +
                         (regions_lat[i] - regions_lat[j]) ** 2)
                for j in range(n) if j != i
            )
            radius = np.clip(nearest * shrink_factor, min_radius, max_radius)
        else:
            radius = min_radius

        circ_lon, circ_lat = generate_circle_coords(regions_lon[i], regions_lat[i], radius)
        all_lons.extend(circ_lon)
        all_lats.extend(circ_lat)
        all_lons.append(None)
        all_lats.append(None)

    return all_lons, all_lats


def emission_to_marker_size(emissions, all_emissions, min_size=6, max_size=22):
    """
    Scales a plant's marker size by its emissions, relative to the other
    plants in the same result set (log scale, since emissions volumes
    usually span orders of magnitude within one sector). Falls back to a
    flat mid-size if all values are equal or the set is too small to scale.
    """
    if not all_emissions or max(all_emissions) <= 0:
        return (min_size + max_size) / 2

    log_vals = np.log10(np.clip(all_emissions, 1e-6, None))
    lo, hi = log_vals.min(), log_vals.max()

    if hi - lo < 1e-9:
        return (min_size + max_size) / 2

    log_e = np.log10(max(emissions, 1e-6))
    t = (log_e - lo) / (hi - lo)
    return min_size + t * (max_size - min_size)


@st.cache_data(show_spinner=False, ttl=60 * 60)  # cache for 1h
def load_pipe_base_config():
    """
    Loads pipe/config/base.yaml — the same static settings PipelineBase.parse_config()
    reads before merging in the per-run case.yaml. Shared by fetch_plants_for_sector()
    and the RUN section below, so column names (source_lat_col, etc.) live in one
    place instead of being hardcoded twice.
    """
    with open(f"{os.getcwd()}/pipe/config/base.yaml", "r") as f:
        return yaml.safe_load(f)


@st.cache_data(show_spinner=False, ttl=60 * 60)  # cache for 1h
def fetch_plants_for_sector(country, sector):
    """
    Pulls emission source ("plant") locations for a given country + sector
    directly from the pipeline's own source API — the same call
    call_source_load() makes in pipe/pipe_flow/pipe_flow.py, and the same
    raw asset shape source_edit() parses in pipe/functions/functions_I.py
    (Id, Name, EmissionsSummary[0].EmissionsQuantity, Centroid.Geometry).

    Deliberately skips get_region() here — that does a reverse-geocoding
    HTTP call PER PLANT with a 1s sleep between calls (see source_edit),
    which is fine for a one-off pipeline run but far too slow for an
    interactive map with potentially hundreds of plants. Region tagging
    still happens later, inside the actual RUN step, exactly as before.

    Returns a list of dicts: {"name", "lat", "lon", "emissions"}.
    """
    try:
        pipe_config = load_pipe_base_config()

        params = {
            "limit": pipe_config["limit"],
            "countries": country_name_to_alpha3(country),
            "year": pipe_config["year"],
            "subsectors": sector,
        }

        raw_assets = source_import_api(pipe_config["source_api_url"], params)
    except Exception as e:
        st.caption(f"⚠️ Could not load plants: {e}")
        return []

    plants = []
    for asset in raw_assets:
        try:
            if asset.get("Id") is None:
                continue
            emissions = float(asset["EmissionsSummary"][0]["EmissionsQuantity"])
            if emissions <= 0:
                continue
            plants.append({
                "name": asset["Name"],
                "lat": float(asset["Centroid"]["Geometry"][1]),
                "lon": float(asset["Centroid"]["Geometry"][0]),
                "emissions": emissions,
            })
        except (KeyError, IndexError, TypeError, ValueError):
            continue  # skip malformed entries rather than failing the whole batch

    return plants


def build_world_figure():
    """Full globe with highlighted countries, no zoom."""
    fig = go.Figure()

    fig.add_trace(go.Choropleth(
        locations=highlighted_countries_codes,
        z=[1] * len(highlighted_countries_codes),
        colorscale=[[0, HIGHLIGHT_COLOR], [1, HIGHLIGHT_COLOR]],
        showscale=False,
        marker_line_color=BORDER_COLOR,
        marker_line_width=1.5,
        geo='geo',
        text=hover_texts,
        hoverinfo='text',
        hovertemplate='%{text}<extra></extra>',
        name='GLOBE',
        customdata=highlighted_countries_names
    ))

    fig.update_layout(
        geo=dict(
            showland=True,
            landcolor=BACKGROUND_COLOR,
            showocean=True,
            oceancolor=OCEAN_COLOR,
            showcountries=True,
            countrycolor='rgba(0, 80, 200, 0.4)',
            countrywidth=1.5,
            showcoastlines=True,
            coastlinecolor='rgb(0, 80, 200)',
            projection=dict(
                type='orthographic',
                scale=0.9,
                rotation=dict(lon=50, lat=21, roll=0)
            ),
            bgcolor='rgba(0, 0, 0, 0)',
            showframe=False,
            lataxis=dict(showgrid=False),
            lonaxis=dict(showgrid=False),
        ),
        paper_bgcolor='rgba(0, 0, 0, 0)',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        margin=dict(l=0, r=0, t=0, b=0),
        dragmode='pan',
        autosize=True
    )
    return fig


def build_country_figure(regions_names, regions_lon, regions_lat, center_lon, center_lat, scale,
                          plants=None, result_circle=None):
    """
    Zoomed-in globe centered on the selected country, with clickable region
    labels, region perimeter circles, plant markers (sized by emissions) if
    a sector is picked, and a RESULT_CIRCLE layer once RUN has computed the
    new-forest area for a selected region or single plant.

    Trace order matters for click handling in the code below (curve_number):
        0 = GLOBE (countries, still clickable)
        1 = REGIONS (clickable text labels)
        2 = REGION_PERIMETERS (circles, display only)
        3 = PLANTS (dots, clickable to pick a single site)
        4 = RESULT_CIRCLE (display only, present only after a RUN)
    Traces 2+ (besides 3) are not read by the click handler, so appending
    new layers after index 1 is always safe.
    """
    fig = go.Figure()

    label_size = region_label_fontsize(len(regions_names))

    # Context layer: still clickable so the user can jump straight to another
    # highlighted country without going back to the world view first.
    fig.add_trace(go.Choropleth(
        locations=highlighted_countries_codes,
        z=[1] * len(highlighted_countries_codes),
        colorscale=[[0, HIGHLIGHT_COLOR], [1, HIGHLIGHT_COLOR]],
        showscale=False,
        marker_line_color=BORDER_COLOR,
        marker_line_width=1.5,
        geo='geo',
        text=hover_texts,
        hoverinfo='text',
        hovertemplate='%{text}<extra></extra>',
        name='GLOBE',
        customdata=highlighted_countries_names
    ))

    # Clickable region labels -> trace index 1 (text only, no dot markers)
    fig.add_trace(go.Scattergeo(
        lon=regions_lon,
        lat=regions_lat,
        mode='text',
        text=regions_names,
        textfont=dict(
            size=label_size,
            color='rgb(150, 20, 20)',
            family='Arial Black, Arial, sans-serif',
        ),
        textposition='middle center',
        hoverinfo='text',
        hovertemplate='<b>%{text}</b><extra></extra>',
        name='REGIONS',
        customdata=regions_names,
    ))

    # Region perimeters -> trace index 2, display only
    circle_lon, circle_lat = build_region_circle_traces_data(regions_lon, regions_lat)
    fig.add_trace(go.Scattergeo(
        lon=circle_lon,
        lat=circle_lat,
        mode='lines',
        line=dict(width=1.2, color='rgba(150, 20, 20, 0.6)'),
        hoverinfo='skip',
        name='REGION_PERIMETERS',
    ))

    # Plants for the selected sector -> trace index 3, display only.
    # Marker size is scaled by emissions (log scale, relative to the other
    # plants shown) rather than by a footprint circle, since a plant's
    # actual land footprint isn't known until the RUN step computes the
    # offsetting forest area (see forest_calculation / new_area_radius).
    if plants:
        plant_lons = [p['lon'] for p in plants]
        plant_lats = [p['lat'] for p in plants]
        plant_emissions = [p['emissions'] for p in plants]
        plant_sizes = [emission_to_marker_size(e, plant_emissions) for e in plant_emissions]
        plant_texts = [
            f"{p['name']}<br>Emissions: {p['emissions']:,.0f}" for p in plants
        ]

        fig.add_trace(go.Scattergeo(
            lon=plant_lons,
            lat=plant_lats,
            mode='markers',
            marker=dict(
                size=plant_sizes,
                color=PLANT_COLOR,
                line=dict(width=1, color='white'),
                symbol='circle',
                opacity=0.85,
            ),
            text=plant_texts,
            hoverinfo='text',
            hovertemplate='%{text}<extra></extra>',
            name='PLANTS',
        ))

    # Result circle -> trace index 4 (only present after RUN has computed a
    # new-forest area for the currently selected region or single plant).
    # Drawn as an outline plus an invisible center marker so hovering the
    # middle of the circle surfaces the label (hovering a thin line ring is
    # fiddly, a center point is a much easier target).
    if result_circle:
        circ_lon, circ_lat = generate_circle_coords(
            result_circle['center_lon'], result_circle['center_lat'], result_circle['radius_deg'], n_points=64
        )
        fig.add_trace(go.Scattergeo(
            lon=circ_lon,
            lat=circ_lat,
            mode='lines',
            line=dict(width=3, color=RESULT_CIRCLE_COLOR),
            hoverinfo='skip',
            name='RESULT_CIRCLE',
        ))
        fig.add_trace(go.Scattergeo(
            lon=[result_circle['center_lon']],
            lat=[result_circle['center_lat']],
            mode='markers',
            marker=dict(size=1, color=RESULT_CIRCLE_COLOR, opacity=0),
            text=[result_circle['label']],
            hoverinfo='text',
            hovertemplate='%{text}<extra></extra>',
            name='RESULT_CIRCLE_LABEL',
        ))

    fig.update_layout(
        geo=dict(
            showland=True,
            landcolor=BACKGROUND_COLOR,
            showocean=True,
            oceancolor=OCEAN_COLOR,
            showcountries=True,
            countrycolor='rgba(0, 80, 200, 0.4)',
            countrywidth=1.5,
            showcoastlines=True,
            coastlinecolor='rgb(0, 80, 200)',
            projection=dict(
                type='orthographic',
                scale=scale,
                rotation=dict(lon=center_lon, lat=center_lat, roll=0)
            ),
            bgcolor='rgba(0, 0, 0, 0)',
            showframe=False,
            lataxis=dict(showgrid=False),
            lonaxis=dict(showgrid=False),
        ),
        paper_bgcolor='rgba(0, 0, 0, 0)',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        margin=dict(l=0, r=0, t=0, b=0),
        dragmode='pan',
        autosize=True
    )
    return fig


##########################
# --- HELPER: GET SECTOR SUMMARY ---
##########################

def get_sector_summary(country, sector, plants):
    """
    Generate summary statistics for the selected country and sector.
    Returns a dict with key metrics.
    """
    if not plants:
        return None
    
    total_emissions = sum(p['emissions'] for p in plants)
    num_plants = len(plants)
    avg_emissions = total_emissions / num_plants if num_plants > 0 else 0
    max_emissions = max(p['emissions'] for p in plants) if plants else 0
    min_emissions = min(p['emissions'] for p in plants) if plants else 0
    
    return {
        'total_emissions': total_emissions,
        'num_plants': num_plants,
        'avg_emissions': avg_emissions,
        'max_emissions': max_emissions,
        'min_emissions': min_emissions,
    }


##########################
# --- LAYOUT: TWO COLUMNS ---
##########################

# Create two columns: globe (larger) and controls/data (smaller)
col_globe, col_sidebar = st.columns([2, 1])

##########################
# --- LEFT COLUMN: GLOBE ---
##########################

with col_globe:
    # --- BUILD CURRENT FIG ---
    regions_names, regions_lon, regions_lat = [], [], []
    plants = []

    if st.session_state.view == "world":
        globe = build_world_figure()
    else:
        raw_names, raw_lon, raw_lat = load_regions(st.session_state.selected_country)
        regions_names, regions_lon, regions_lat, dropped_regions = filter_valid_coordinates(
            raw_names, raw_lon, raw_lat
        )

        if dropped_regions:
            st.caption(
                f"⚠️ Skipped {len(dropped_regions)} region(s) with missing/invalid coordinates: "
                f"{', '.join(dropped_regions)}"
            )

        if regions_lon and regions_lat:
            center_lon = np.mean(regions_lon)
            center_lat = np.mean(regions_lat)
            zoom_scale = compute_zoom_scale(regions_lon, regions_lat)

            if st.session_state.selected_sector != 'Select sector':
                with st.spinner(f"Loading {st.session_state.selected_sector} plants..."):
                    plants = fetch_plants_for_sector(st.session_state.selected_country, st.session_state.selected_sector)

                if not plants:
                    st.caption(
                        f"No {st.session_state.selected_sector} plants found for "
                        f"{st.session_state.selected_country}."
                    )

            globe = build_country_figure(
                regions_names, regions_lon, regions_lat, center_lon, center_lat, zoom_scale,
                plants=plants, result_circle=st.session_state.result_circle
            )
        else:
            st.warning(f"No valid region data available for {st.session_state.selected_country}.")
            globe = build_world_figure()
            st.session_state.view = "world"
            st.session_state.selected_country = None

    # Single chart call
    chart_key = (
        f"globe_{st.session_state.view}_{st.session_state.selected_country}_"
        f"{st.session_state.selected_sector}_{bool(st.session_state.result_circle)}"
    )

    selected_points = plotly_events(
        globe,
        click_event=True,
        select_event=False,
        hover_event=False,
        override_height=800,
        key=chart_key,
    )


##########################
# --- RIGHT COLUMN: CONTROLS & SUMMARY ---
##########################

with col_sidebar:
    # Back button (only when in country view)
    if st.session_state.view == "country":
        if st.button("⬅ Back to world view", use_container_width=True):
            st.session_state.view = "world"
            st.session_state.selected_country = None
            st.session_state.selected_region = None
            st.session_state.selected_site = None
            st.session_state.selected_sector = 'Select sector'
            st.session_state.result_circle = None
            st.session_state.df_result = None
            st.rerun()
    
    # Country/Region/Site info
    if st.session_state.view == "country":
        st.markdown(f"### {st.session_state.selected_country}")
        
        # Region and site are mutually exclusive — show whichever is active.
        if st.session_state.selected_site:
            selection_line = f"**Plant:** {st.session_state.selected_site}"
        elif st.session_state.selected_region:
            selection_line = f"**Region:** {st.session_state.selected_region}"
        else:
            selection_line = "Click a region label or a plant marker to select one"
        
        st.markdown(selection_line)
        st.divider()
    
    # Sector select box
    st.session_state.selected_sector = st.selectbox(
        "Sector",
        options=SECTOR_OPTIONS,
        index=SECTOR_OPTIONS.index(st.session_state.selected_sector)
                if st.session_state.selected_sector in SECTOR_OPTIONS else 0,
        key="sector_selectbox"
    )
    
    # Summary info for selected country/sector
    if st.session_state.view == "country" and st.session_state.selected_sector != 'Select sector':
        if plants:  # plants is available from the globe building section above
            summary = get_sector_summary(st.session_state.selected_country, st.session_state.selected_sector, plants)
            if summary:
                st.markdown("### Sector Summary")
                
                # Format emissions with commas
                total_emissions_formatted = f"{summary['total_emissions']:,.0f}"
                avg_emissions_formatted = f"{summary['avg_emissions']:,.0f}"
                max_emissions_formatted = f"{summary['max_emissions']:,.0f}"
                min_emissions_formatted = f"{summary['min_emissions']:,.0f}"
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Emissions", f"{total_emissions_formatted}")
                    st.metric("Avg Emissions", f"{avg_emissions_formatted}")
                with col2:
                    st.metric("Number of Plants", f"{summary['num_plants']}")
                    st.metric("Max Emissions", f"{max_emissions_formatted}")
                
                st.divider()
        else:
            st.info("No plants found for this sector/country combination.")
    
    # RUN button
    selected_country = str(st.session_state.selected_country)
    selected_region = str(st.session_state.selected_region)
    selected_site = str(st.session_state.selected_site)
    selected_sector = st.session_state.selected_sector
    
    DEG_PER_KM = 1 / 111.32
    
    if selected_country != 'None' and selected_sector != 'Select sector':
        if st.button("RUN", use_container_width=True):
            with open(f"{os.getcwd()}/pipe/config/case.yaml", 'w') as f:
                data = {
                    "country": selected_country,
                    "sector": selected_sector,
                    "region": selected_region if selected_region != 'None' else 'None',
                    "site": selected_site if selected_site != 'None' else 'None',
                }
                yaml.dump(data, f, default_flow_style=False)
            
            with st.spinner("Work in progress..."):
                main()
            
            pipe_config = load_pipe_base_config()
            lat_col = pipe_config['source_lat_col']
            lon_col = pipe_config['source_lon_col']
            
            # Which output to read back depends on which of region/site was set
            if selected_site != 'None':
                result_key = selected_site
            elif selected_region != 'None':
                result_key = selected_region
            else:
                result_key = selected_country
            
            result_path = f"{os.getcwd()}/output/csv/{result_key}/forest_result.csv"
            df_result = pd.read_csv(result_path)
            st.session_state.df_result = df_result
            
            if selected_site != 'None':
                row = df_result.iloc[0]
                radius_km = float(row['new_area_radius'])
                st.session_state.result_circle = {
                    'center_lon': float(row[lon_col]),
                    'center_lat': float(row[lat_col]),
                    'radius_deg': radius_km * DEG_PER_KM,
                    'label': f"{selected_site}: {row['new_forest']:,.0f} ha new forest needed",
                }
            elif selected_region != 'None':
                total_new_forest = float(df_result['new_forest'].sum())
                total_radius_km = hectares_to_circle_radius(total_new_forest)
                
                if selected_region in regions_names:
                    idx = regions_names.index(selected_region)
                    center_lon, center_lat = regions_lon[idx], regions_lat[idx]
                else:
                    center_lon, center_lat = float(df_result[lon_col].mean()), float(df_result[lat_col].mean())
                
                st.session_state.result_circle = {
                    'center_lon': center_lon,
                    'center_lat': center_lat,
                    'radius_deg': total_radius_km * DEG_PER_KM,
                    'label': f"{selected_region}: {total_new_forest:,.0f} ha new forest needed (total)",
                }
            else:
                st.session_state.result_circle = None
            
            st.rerun()


##########################
# --- DATAFRAME UNDERNEATH ---
##########################

# Display dataframe if available (full width, underneath both columns)
if st.session_state.df_result is not None:
    st.divider()
    st.subheader("📋 Forest Results")
    st.dataframe(pd.DataFrame(st.session_state.df_result)[['name','emission','lat_source','lon_source','region','new_forest','new_area_radius']], use_container_width=True, hide_index=True)


##########################
# --- HANDLE CLICKS ------
##########################

if selected_points:
    clicked = selected_points[0]
    curve_number = clicked.get('curveNumber', 0)
    point_index = clicked.get('pointIndex', 0)
    
    if st.session_state.view == "world":
        # Clicked a country on the world globe -> zoom in
        if 0 <= point_index < len(highlighted_countries_names):
            st.session_state.selected_country = highlighted_countries_names[point_index]
            st.session_state.view = "country"
            st.session_state.selected_region = None
            st.session_state.selected_site = None
            st.session_state.selected_sector = 'Select sector'
            st.session_state.result_circle = None
            st.session_state.df_result = None
            st.rerun()
    
    elif st.session_state.view == "country" and curve_number == 0:
        # Clicked a (possibly different) country while already zoomed in
        if 0 <= point_index < len(highlighted_countries_names):
            new_country = highlighted_countries_names[point_index]
            if new_country != st.session_state.selected_country:
                st.session_state.selected_country = new_country
                st.session_state.selected_region = None
                st.session_state.selected_site = None
                st.session_state.selected_sector = 'Select sector'
                st.session_state.result_circle = None
                st.session_state.df_result = None
                st.rerun()
    
    elif st.session_state.view == "country" and curve_number == 1:
        # Clicked a region label -> select region, clear any single-plant selection
        if 0 <= point_index < len(regions_names):
            st.session_state.selected_region = regions_names[point_index]
            st.session_state.selected_site = None
            st.session_state.result_circle = None
            st.session_state.df_result = None
            st.rerun()
    
    elif st.session_state.view == "country" and curve_number == 3:
        # Clicked a plant marker -> select that single plant as the "site"
        if plants and 0 <= point_index < len(plants):
            st.session_state.selected_site = plants[point_index]['name']
            st.session_state.selected_region = None
            st.session_state.result_circle = None
            st.session_state.df_result = None
            st.rerun()