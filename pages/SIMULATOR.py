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


# --- LOGO-TITLE ---
# col1, col2, col3 = st.columns([1, 2, 1])
# with col2:
#     st.image(f"{os.getcwd()}/LOGO.png")

# st.divider()

# -- HEADER ---
st.title("🌱 SIMULATOR")
st.header("Select country:")
# st.markdown('#')


##########################
# --- STATIC RESOURCES ---
##########################

highlighted_countries_names = config['countries']
highlighted_countries_codes = [country_name_to_alpha3(country) for country in config['countries']]

# Colors
HIGHLIGHT_COLOR = "rgba(0, 255, 0, 0.5)"
BORDER_COLOR = "rgb(0, 80, 200)"
BACKGROUND_COLOR = "rgb(245, 248, 250)"
OCEAN_COLOR = "rgb(220, 235, 255)"

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
    far in either direction. Both empirical constants (40.0 and 6.0) are
    tuning knobs: raise them to zoom out more under that constraint, lower
    them to zoom in more.
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

    A single NaN coordinate silently poisons every downstream calculation
    that touches it (np.mean, cos, distance checks, ...) and eventually
    surfaces as Plotly rejecting a 'scale' of nan, so it has to be filtered
    out here, before any of that math runs.
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
    circle around every region's centroid. Each circle's radius is sized
    from that region's distance to its nearest neighbor, so circles in
    dense clusters shrink to avoid overlapping, while isolated regions get
    a more generous circle.
    """
    n = len(regions_lon)
    all_lons, all_lats = [], []

    for i in range(n):
        if n > 1:
            # distance (in degrees, longitude-compressed) to the nearest other region
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


def build_country_figure(regions_names, regions_lon, regions_lat, center_lon, center_lat, scale):
    """Zoomed-in globe centered on the selected country, with clickable region markers."""
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

    # Region perimeters, approximated as a circle around each centroid,
    # sized from that region's spacing to its nearest neighbor so dense
    # clusters don't overlap. Trace index 2, after GLOBE (0) and REGIONS (1),
    # so existing click handling by curve_number is unaffected.
    circle_lon, circle_lat = build_region_circle_traces_data(regions_lon, regions_lat)
    fig.add_trace(go.Scattergeo(
        lon=circle_lon,
        lat=circle_lat,
        mode='lines',
        line=dict(width=1.2, color='rgba(150, 20, 20, 0.6)'),
        hoverinfo='skip',
        name='REGION_PERIMETERS',
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
# --- BUILD CURRENT FIG --
##########################

regions_names, regions_lon, regions_lat = [], [], []

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
        globe = build_country_figure(
            regions_names, regions_lon, regions_lat, center_lon, center_lat, zoom_scale
        )
    else:
        st.warning(f"No valid region data available for {st.session_state.selected_country}.")
        globe = build_world_figure()
        st.session_state.view = "world"
        st.session_state.selected_country = None


##########################
# --- SINGLE CHART CALL --
##########################

# Key changes whenever the view or selected country changes, forcing a clean
# remount of the component. This prevents plotly_events from replaying a
# stale click (e.g. a region click) against the next figure after navigating,
# which was causing IndexError / "random country" jumps on Back.
chart_key = f"globe_{st.session_state.view}_{st.session_state.selected_country}"

selected_points = plotly_events(
    globe,
    click_event=True,
    select_event=False,
    hover_event=False,
    override_height=800,
    key=chart_key,
)


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
            st.rerun()

    elif st.session_state.view == "country" and curve_number == 0:
        # Clicked a (possibly different) country while already zoomed in
        if 0 <= point_index < len(highlighted_countries_names):
            new_country = highlighted_countries_names[point_index]
            if new_country != st.session_state.selected_country:
                st.session_state.selected_country = new_country
                st.session_state.selected_region = None
                st.rerun()

    elif st.session_state.view == "country" and curve_number == 1:
        # Clicked a region marker on the zoomed-in globe
        if 0 <= point_index < len(regions_names):
            st.session_state.selected_region = regions_names[point_index]


##########################
# --- COUNTRY HEADER -----
##########################

if st.session_state.view == "country":
    if st.button("⬅ Back to world view"):
        st.session_state.view = "world"
        st.session_state.selected_country = None
        st.session_state.selected_region = None
        st.rerun()

    st.markdown(
        f"<h1 style='text-align: center;'>{st.session_state.selected_country}</h1>",
        unsafe_allow_html=True
    )
    st.divider()


##########################
# --- REGION POPUP -------
##########################

if st.session_state.selected_region:
    st.markdown(
        f"""
        <div style="
            border: 2px solid rgb(0, 80, 200);
            border-radius: 12px;
            padding: 16px;
            background-color: white;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            margin-top: 12px;
        ">
            <h3 style="margin:0;">📍 {st.session_state.selected_region}</h3>
            <p style="margin:4px 0 0 0; color: gray;">Region of {st.session_state.selected_country}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("#")
    # --- Region-level simulator content goes here ---
    st.write(f"Add your region-level simulator content for **{st.session_state.selected_region}** here.")