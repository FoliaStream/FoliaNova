# import streamlit as st
# import plotly.graph_objects as go
# import pandas as pd
# import pydeck as pdk
# import numpy as np

# import os
# import yaml

# from streamlit_plotly_events import plotly_events

# from src.functions_fe.simulator_functions import compute_zoom_scale, region_label_fontsize, filter_valid_coordinates, generate_circle_coords, build_region_circle_traces_data, emission_to_marker_size, get_sector_summary
# from src.functions_fe.sidebar import setup_sidebar
# from src.functions_fe.styles import HIDE_SIDEBAR_NAV
# from src.functions_fe.helpers_functions import country_name_to_alpha3, load_regions
# # from src.functions_fe.load_regions import load_regions
# from pipe.functions.functions_I import source_import_api
# from pipe.functions.functions_II import hectares_to_circle_radius
# from pipe.streamain import main



# ################
# # --- SET UP ---
# ################

# # --- PAGE CONFIG ---
# st.set_page_config(page_title="FoliaNova - SIMULATOR", layout="wide")

# # --- STYLES ---
# st.markdown(HIDE_SIDEBAR_NAV, unsafe_allow_html=True)

# # --- CONFIG ---
# with open(f"{os.getcwd()}/src/config_fe/config.yaml", "r") as config_file:
#     config = yaml.safe_load(config_file)

# # --- SIDEBAR & TITLE ---
# selected_page = setup_sidebar(
#     pages=config['pages'],
#     main_page=config['main_page']
# )

# # Navigation on click
# if selected_page == "HOME":
#     st.switch_page("HOME.py")
# elif selected_page == "SIMULATOR":
#     pass
# elif selected_page == "OVERVIEW":
#     st.switch_page("pages/OVERVIEW.py")

# # -- HEADER ---
# st.title("🌱 SIMULATOR")


# ##########################
# # --- STATIC RESOURCES ---
# ##########################

# highlighted_countries_names = config['countries']
# highlighted_countries_codes = [country_name_to_alpha3(country) for country in config['countries']]

# SECTOR_OPTIONS = [
#     'Select sector',
#     "electricity-generation", "cement", "aluminum", "pulp-and-paper",
#     "chemicals", "oil-and-gas-refining", "coal-mining", "bauxite-mining",
#     "iron-mining", "copper-mining"
# ]

# # Colors
# HIGHLIGHT_COLOR = "rgba(0, 255, 0, 0.5)"
# BORDER_COLOR = "rgb(0, 80, 200)"
# BACKGROUND_COLOR = "rgb(245, 248, 250)"
# OCEAN_COLOR = "rgb(220, 235, 255)"
# PLANT_COLOR = "rgb(255, 140, 0)"
# RESULT_CIRCLE_COLOR = "rgb(120, 0, 200)"

# # Hover texts for the world view
# hover_texts = []
# for country in highlighted_countries_names:
#     hover_texts.append(f"<span style='font-size: 20px;'>{country}</span><b></b><br>")


# ##########################
# # --- SESSION STATE -----
# ##########################

# if "view" not in st.session_state:
#     st.session_state.view = "world"          # "world" or "country"
# if "selected_country" not in st.session_state:
#     st.session_state.selected_country = None
# if "selected_region" not in st.session_state:
#     st.session_state.selected_region = None
# if "selected_site" not in st.session_state:
#     st.session_state.selected_site = None          # a single plant name, mutually exclusive with selected_region
# if "selected_sector" not in st.session_state:
#     st.session_state.selected_sector = 'Select sector'
# if "result_circle" not in st.session_state:
#     st.session_state.result_circle = None          # dict: center_lon, center_lat, radius_deg, label — set after RUN
# if "df_result" not in st.session_state:
#     st.session_state.df_result = None


# ##########################
# # --- FIGURE BUILDERS ---
# ##########################


# # @st.cache_data(show_spinner=False, ttl=60 * 60)  # cache for 1h
# # Import pipeline base

# def load_pipe_base_config():

#     with open(f"{os.getcwd()}/pipe/config/base.yaml", "r") as f:

#         return yaml.safe_load(f)


# # @st.cache_data(show_spinner=False, ttl=60 * 60)  # cache for 1h
# # same as call_source_load but skip get_region to avoid wait time API
# def fetch_plants_for_sector(country, sector):

#     try:
#         pipe_config = load_pipe_base_config()

#         params = {
#             "limit": pipe_config["limit"],
#             "countries": country_name_to_alpha3(country),
#             "year": pipe_config["year"],
#             "subsectors": sector,
#         }

#         raw_assets = source_import_api(pipe_config["source_api_url"], params)
#     except Exception as e:
#         st.caption(f"⚠️ Could not load plants: {e}")
#         return []

#     plants = []
#     for asset in raw_assets:
#         try:
#             if asset.get("Id") is None:
#                 continue
#             emissions = float(asset["EmissionsSummary"][0]["EmissionsQuantity"])
#             if emissions <= 0:
#                 continue
#             plants.append({
#                 "name": asset["Name"],
#                 "lat": float(asset["Centroid"]["Geometry"][1]),
#                 "lon": float(asset["Centroid"]["Geometry"][0]),
#                 "emissions": emissions,
#             })
#         except (KeyError, IndexError, TypeError, ValueError):
#             continue  # skip malformed entries rather than failing the whole batch

#     return plants


# # Globe figure
# def build_world_figure():

#     fig = go.Figure()

#     fig.add_trace(go.Choropleth(
#         locations=highlighted_countries_codes,
#         z=[1] * len(highlighted_countries_codes),
#         colorscale=[[0, HIGHLIGHT_COLOR], [1, HIGHLIGHT_COLOR]],
#         showscale=False,
#         marker_line_color=BORDER_COLOR,
#         marker_line_width=1.5,
#         geo='geo',
#         text=hover_texts,
#         hoverinfo='text',
#         hovertemplate='%{text}<extra></extra>',
#         name='GLOBE',
#         customdata=highlighted_countries_names
#     ))

#     fig.update_layout(
#         geo=dict(
#             showland=True,
#             landcolor=BACKGROUND_COLOR,
#             showocean=True,
#             oceancolor=OCEAN_COLOR,
#             showcountries=True,
#             countrycolor='rgba(0, 80, 200, 0.4)',
#             countrywidth=1.5,
#             showcoastlines=True,
#             coastlinecolor='rgb(0, 80, 200)',
#             projection=dict(
#                 type='orthographic',
#                 scale=0.9,
#                 rotation=dict(lon=50, lat=21, roll=0)
#             ),
#             bgcolor='rgba(0, 0, 0, 0)',
#             showframe=False,
#             lataxis=dict(showgrid=False),
#             lonaxis=dict(showgrid=False),
#         ),
#         paper_bgcolor='rgba(0, 0, 0, 0)',
#         plot_bgcolor='rgba(0, 0, 0, 0)',
#         margin=dict(l=0, r=0, t=0, b=0),
#         dragmode='pan',
#         autosize=True
#     )
#     return fig


# # Globe zoomed in the selected country figure
# def build_country_figure(regions_names, regions_lon, regions_lat, center_lon, center_lat, scale,
#                           plants=None, result_circle=None):
#     """
#     Zoomed-in globe centered on the selected country, with clickable region
#     labels, region perimeter circles, plant markers (sized by emissions) if
#     a sector is picked, and a RESULT_CIRCLE layer once RUN has computed the
#     new-forest area for a selected region or single plant.

#     Trace order matters for click handling in the code below (curve_number):
#         0 = GLOBE (countries, still clickable)
#         1 = REGIONS (clickable text labels)
#         2 = REGION_PERIMETERS (circles, display only)
#         3 = PLANTS (dots, clickable to pick a single site)
#         4 = RESULT_CIRCLE (display only, present only after a RUN)
#     Traces 2+ (besides 3) are not read by the click handler, so appending
#     new layers after index 1 is always safe.
#     """
#     fig = go.Figure()

#     label_size = region_label_fontsize(len(regions_names))

#     # Context layer: still clickable so the user can jump straight to another highlighted country without going back to the world view first.
#     fig.add_trace(go.Choropleth(
#         locations=highlighted_countries_codes,
#         z=[1] * len(highlighted_countries_codes),
#         colorscale=[[0, HIGHLIGHT_COLOR], [1, HIGHLIGHT_COLOR]],
#         showscale=False,
#         marker_line_color=BORDER_COLOR,
#         marker_line_width=1.5,
#         geo='geo',
#         text=hover_texts,
#         hoverinfo='text',
#         hovertemplate='%{text}<extra></extra>',
#         name='GLOBE',
#         customdata=highlighted_countries_names
#     ))

#     # Clickable region labels -> trace index 1 (text only, no dot markers)
#     fig.add_trace(go.Scattergeo(
#         lon=regions_lon,
#         lat=regions_lat,
#         mode='text',
#         text=regions_names,
#         textfont=dict(
#             size=label_size,
#             color='rgb(150, 20, 20)',
#             family='Arial Black, Arial, sans-serif',
#         ),
#         textposition='middle center',
#         hoverinfo='text',
#         hovertemplate='<b>%{text}</b><extra></extra>',
#         name='REGIONS',
#         customdata=regions_names,
#     ))

#     # Region perimeters -> trace index 2, display only
#     circle_lon, circle_lat = build_region_circle_traces_data(regions_lon, regions_lat)
#     fig.add_trace(go.Scattergeo(
#         lon=circle_lon,
#         lat=circle_lat,
#         mode='lines',
#         line=dict(width=1.2, color='rgba(150, 20, 20, 0.6)'),
#         hoverinfo='skip',
#         name='REGION_PERIMETERS',
#     ))

#     # Plants for the selected sector -> trace index 3, display only.
#     # Marker size is scaled by emissions (log scale, relative to the other
#     # plants shown) rather than by a footprint circle, since a plant's
#     # actual land footprint isn't known until the RUN step computes the
#     # offsetting forest area (see forest_calculation / new_area_radius).
#     if plants:
#         plant_lons = [p['lon'] for p in plants]
#         plant_lats = [p['lat'] for p in plants]
#         plant_emissions = [p['emissions'] for p in plants]
#         plant_sizes = [emission_to_marker_size(e, plant_emissions) for e in plant_emissions]
#         plant_texts = [
#             f"{p['name']}<br>Emissions: {p['emissions']:,.0f}" for p in plants
#         ]

#         fig.add_trace(go.Scattergeo(
#             lon=plant_lons,
#             lat=plant_lats,
#             mode='markers',
#             marker=dict(
#                 size=plant_sizes,
#                 color=PLANT_COLOR,
#                 line=dict(width=1, color='white'),
#                 symbol='circle',
#                 opacity=0.85,
#             ),
#             text=plant_texts,
#             hoverinfo='text',
#             hovertemplate='%{text}<extra></extra>',
#             name='PLANTS',
#         ))

#     # Result circle -> trace index 4 (only present after RUN has computed a
#     # new-forest area for the currently selected region or single plant).
#     # Drawn as an outline plus an invisible center marker so hovering the
#     # middle of the circle surfaces the label (hovering a thin line ring is
#     # fiddly, a center point is a much easier target).
#     if result_circle:
#         circ_lon, circ_lat = generate_circle_coords(
#             result_circle['center_lon'], result_circle['center_lat'], result_circle['radius_deg'], n_points=64
#         )
#         fig.add_trace(go.Scattergeo(
#             lon=circ_lon,
#             lat=circ_lat,
#             mode='lines',
#             line=dict(width=3, color=RESULT_CIRCLE_COLOR),
#             hoverinfo='skip',
#             name='RESULT_CIRCLE',
#         ))
#         fig.add_trace(go.Scattergeo(
#             lon=[result_circle['center_lon']],
#             lat=[result_circle['center_lat']],
#             mode='markers',
#             marker=dict(size=1, color=RESULT_CIRCLE_COLOR, opacity=0),
#             text=[result_circle['label']],
#             hoverinfo='text',
#             hovertemplate='%{text}<extra></extra>',
#             name='RESULT_CIRCLE_LABEL',
#         ))

#     fig.update_layout(
#         geo=dict(
#             showland=True,
#             landcolor=BACKGROUND_COLOR,
#             showocean=True,
#             oceancolor=OCEAN_COLOR,
#             showcountries=True,
#             countrycolor='rgba(0, 80, 200, 0.4)',
#             countrywidth=1.5,
#             showcoastlines=True,
#             coastlinecolor='rgb(0, 80, 200)',
#             projection=dict(
#                 type='orthographic',
#                 scale=scale,
#                 rotation=dict(lon=center_lon, lat=center_lat, roll=0)
#             ),
#             bgcolor='rgba(0, 0, 0, 0)',
#             showframe=False,
#             lataxis=dict(showgrid=False),
#             lonaxis=dict(showgrid=False),
#         ),
#         paper_bgcolor='rgba(0, 0, 0, 0)',
#         plot_bgcolor='rgba(0, 0, 0, 0)',
#         margin=dict(l=0, r=0, t=0, b=0),
#         dragmode='pan',
#         autosize=True
#     )
#     return fig





# ##########################
# # --- LAYOUT: TWO COLUMNS ---
# ##########################

# # Create two columns: globe (larger) and controls/data (smaller)
# col_globe, col_sidebar = st.columns([2, 1])

# ##########################
# # --- LEFT COLUMN: GLOBE ---
# ##########################

# with col_globe:
#     # --- BUILD CURRENT FIG ---
#     regions_names, regions_lon, regions_lat = [], [], []
#     plants = []

#     if st.session_state.view == "world":
#         globe = build_world_figure()
#     else:
#         raw_names, raw_lon, raw_lat = load_regions(st.session_state.selected_country)
#         regions_names, regions_lon, regions_lat, dropped_regions = filter_valid_coordinates(
#             raw_names, raw_lon, raw_lat
#         )

#         if dropped_regions:
#             st.caption(
#                 f"⚠️ Skipped {len(dropped_regions)} region(s) with missing/invalid coordinates: "
#                 f"{', '.join(dropped_regions)}"
#             )

#         if regions_lon and regions_lat:
#             center_lon = np.mean(regions_lon)
#             center_lat = np.mean(regions_lat)
#             zoom_scale = compute_zoom_scale(regions_lon, regions_lat)

#             if st.session_state.selected_sector != 'Select sector':
#                 with st.spinner(f"Loading {st.session_state.selected_sector} plants..."):
#                     plants = fetch_plants_for_sector(st.session_state.selected_country, st.session_state.selected_sector)

#                 if not plants:
#                     st.caption(
#                         f"No {st.session_state.selected_sector} plants found for "
#                         f"{st.session_state.selected_country}."
#                     )

#             globe = build_country_figure(
#                 regions_names, regions_lon, regions_lat, center_lon, center_lat, zoom_scale,
#                 plants=plants, result_circle=st.session_state.result_circle
#             )
#         else:
#             st.warning(f"No valid region data available for {st.session_state.selected_country}.")
#             globe = build_world_figure()
#             st.session_state.view = "world"
#             st.session_state.selected_country = None

#     # Single chart call
#     chart_key = (
#         f"globe_{st.session_state.view}_{st.session_state.selected_country}_"
#         f"{st.session_state.selected_sector}_{bool(st.session_state.result_circle)}"
#     )

#     selected_points = plotly_events(
#         globe,
#         click_event=True,
#         select_event=False,
#         hover_event=False,
#         override_height=800,
#         key=chart_key,
#     )


# ##########################
# # --- RIGHT COLUMN: CONTROLS & SUMMARY ---
# ##########################

# with col_sidebar:
#     # Back button (only when in country view)
#     if st.session_state.view == "country":
#         if st.button("⬅ Back to world view", use_container_width=True):
#             st.session_state.view = "world"
#             st.session_state.selected_country = None
#             st.session_state.selected_region = None
#             st.session_state.selected_site = None
#             st.session_state.selected_sector = 'Select sector'
#             st.session_state.result_circle = None
#             st.session_state.df_result = None
#             st.rerun()
    
#     # Country/Region/Site info
#     if st.session_state.view == "country":
#         st.markdown(f"### {st.session_state.selected_country}")
        
#         # Region and site are mutually exclusive — show whichever is active.
#         if st.session_state.selected_site:
#             selection_line = f"**Plant:** {st.session_state.selected_site}"
#         elif st.session_state.selected_region:
#             selection_line = f"**Region:** {st.session_state.selected_region}"
#         else:
#             selection_line = "Click a region label or a plant marker to select one"
        
#         st.markdown(selection_line)
#         st.divider()
    
#     # Sector select box
#     st.session_state.selected_sector = st.selectbox(
#         "Sector",
#         options=SECTOR_OPTIONS,
#         index=SECTOR_OPTIONS.index(st.session_state.selected_sector)
#                 if st.session_state.selected_sector in SECTOR_OPTIONS else 0,
#         key="sector_selectbox"
#     )
    
#     # Summary info for selected country/sector
#     if st.session_state.view == "country" and st.session_state.selected_sector != 'Select sector':
#         if plants:  # plants is available from the globe building section above
#             summary = get_sector_summary(st.session_state.selected_country, st.session_state.selected_sector, plants)
#             if summary:
#                 st.markdown("### Sector Summary")
                
#                 # Format emissions with commas
#                 total_emissions_formatted = f"{summary['total_emissions']:,.0f}"
#                 avg_emissions_formatted = f"{summary['avg_emissions']:,.0f}"
#                 max_emissions_formatted = f"{summary['max_emissions']:,.0f}"
#                 min_emissions_formatted = f"{summary['min_emissions']:,.0f}"
                
#                 col1, col2 = st.columns(2)
#                 with col1:
#                     st.metric("Total Emissions", f"{total_emissions_formatted}")
#                     st.metric("Avg Emissions", f"{avg_emissions_formatted}")
#                 with col2:
#                     st.metric("Number of Plants", f"{summary['num_plants']}")
#                     st.metric("Max Emissions", f"{max_emissions_formatted}")
                
#                 st.divider()
#         else:
#             st.info("No plants found for this sector/country combination.")
    
#     # RUN button
#     selected_country = str(st.session_state.selected_country)
#     selected_region = str(st.session_state.selected_region)
#     selected_site = str(st.session_state.selected_site)
#     selected_sector = st.session_state.selected_sector
    
#     DEG_PER_KM = 1 / 111.32
    
#     if selected_country != 'None' and selected_sector != 'Select sector':
#         if st.button("RUN", use_container_width=True):
#             with open(f"{os.getcwd()}/pipe/config/case.yaml", 'w') as f:
#                 data = {
#                     "country": selected_country,
#                     "sector": selected_sector,
#                     "region": selected_region if selected_region != 'None' else 'None',
#                     "site": selected_site if selected_site != 'None' else 'None',
#                 }
#                 yaml.dump(data, f, default_flow_style=False)
            
#             with st.spinner("Work in progress..."):
#                 main()
            
#             pipe_config = load_pipe_base_config()
#             lat_col = pipe_config['source_lat_col']
#             lon_col = pipe_config['source_lon_col']
            
#             # Which output to read back depends on which of region/site was set
#             if selected_site != 'None':
#                 result_key = selected_site
#             elif selected_region != 'None':
#                 result_key = selected_region
#             else:
#                 result_key = selected_country
            
#             result_path = f"{os.getcwd()}/output/csv/{result_key}/forest_result.csv"
#             df_result = pd.read_csv(result_path)
#             st.session_state.df_result = df_result
            
#             if selected_site != 'None':
#                 row = df_result.iloc[0]
#                 radius_km = float(row['new_area_radius'])
#                 st.session_state.result_circle = {
#                     'center_lon': float(row[lon_col]),
#                     'center_lat': float(row[lat_col]),
#                     'radius_deg': radius_km * DEG_PER_KM,
#                     'label': f"{selected_site}: {row['new_forest']:,.0f} ha new forest needed",
#                 }
#             elif selected_region != 'None':
#                 total_new_forest = float(df_result['new_forest'].sum())
#                 total_radius_km = hectares_to_circle_radius(total_new_forest)
                
#                 if selected_region in regions_names:
#                     idx = regions_names.index(selected_region)
#                     center_lon, center_lat = regions_lon[idx], regions_lat[idx]
#                 else:
#                     center_lon, center_lat = float(df_result[lon_col].mean()), float(df_result[lat_col].mean())
                
#                 st.session_state.result_circle = {
#                     'center_lon': center_lon,
#                     'center_lat': center_lat,
#                     'radius_deg': total_radius_km * DEG_PER_KM,
#                     'label': f"{selected_region}: {total_new_forest:,.0f} ha new forest needed (total)",
#                 }
#             else:
#                 st.session_state.result_circle = None
            
#             st.rerun()


# ##########################
# # --- DATAFRAME UNDERNEATH ---
# ##########################

# # Display dataframe if available (full width, underneath both columns)
# if st.session_state.df_result is not None:
#     st.divider()
#     st.subheader("📋 Forest Results")
#     st.dataframe(pd.DataFrame(st.session_state.df_result)[['name','emission','lat_source','lon_source','region','new_forest','new_area_radius']], use_container_width=True, hide_index=True)


# ##########################
# # --- HANDLE CLICKS ------
# ##########################

# if selected_points:
#     clicked = selected_points[0]
#     curve_number = clicked.get('curveNumber', 0)
#     point_index = clicked.get('pointIndex', 0)
    
#     if st.session_state.view == "world":
#         # Clicked a country on the world globe -> zoom in
#         if 0 <= point_index < len(highlighted_countries_names):
#             st.session_state.selected_country = highlighted_countries_names[point_index]
#             st.session_state.view = "country"
#             st.session_state.selected_region = None
#             st.session_state.selected_site = None
#             st.session_state.selected_sector = 'Select sector'
#             st.session_state.result_circle = None
#             st.session_state.df_result = None
#             st.rerun()
    
#     elif st.session_state.view == "country" and curve_number == 0:
#         # Clicked a (possibly different) country while already zoomed in
#         if 0 <= point_index < len(highlighted_countries_names):
#             new_country = highlighted_countries_names[point_index]
#             if new_country != st.session_state.selected_country:
#                 st.session_state.selected_country = new_country
#                 st.session_state.selected_region = None
#                 st.session_state.selected_site = None
#                 st.session_state.selected_sector = 'Select sector'
#                 st.session_state.result_circle = None
#                 st.session_state.df_result = None
#                 st.rerun()
    
#     elif st.session_state.view == "country" and curve_number == 1:
#         # Clicked a region label -> select region, clear any single-plant selection
#         if 0 <= point_index < len(regions_names):
#             st.session_state.selected_region = regions_names[point_index]
#             st.session_state.selected_site = None
#             st.session_state.result_circle = None
#             st.session_state.df_result = None
#             st.rerun()
    
#     elif st.session_state.view == "country" and curve_number == 3:
#         # Clicked a plant marker -> select that single plant as the "site"
#         if plants and 0 <= point_index < len(plants):
#             st.session_state.selected_site = plants[point_index]['name']
#             st.session_state.selected_region = None
#             st.session_state.result_circle = None
#             st.session_state.df_result = None
#             st.rerun()

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import pydeck as pdk
import numpy as np

import os
import yaml

from streamlit_plotly_events import plotly_events

from src.functions_fe.simulator_functions import compute_zoom_scale, region_label_fontsize, filter_valid_coordinates, generate_circle_coords, build_region_circle_traces_data, emission_to_marker_size, get_sector_summary
from src.functions_fe.sidebar import setup_sidebar
from src.functions_fe.styles import HIDE_SIDEBAR_NAV
from src.functions_fe.helpers_functions import country_name_to_alpha3, load_regions
# from src.functions_fe.load_regions import load_regions
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


# @st.cache_data(show_spinner=False, ttl=60 * 60)  # cache for 1h
# Import pipeline base

def load_pipe_base_config():

    with open(f"{os.getcwd()}/pipe/config/base.yaml", "r") as f:

        return yaml.safe_load(f)


# @st.cache_data(show_spinner=False, ttl=60 * 60)  # cache for 1h
# same as call_source_load but skip get_region to avoid wait time API
def fetch_plants_for_sector(country, sector):

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


# Globe figure
def build_world_figure():

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


# Globe zoomed in the selected country figure
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

    # Context layer: still clickable so the user can jump straight to another highlighted country without going back to the world view first.
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
    # Key includes selected_region/selected_site (not just view/country/sector/
    # result_circle), so EVERY distinct click — country, region, or plant —
    # forces plotly_events to remount cleanly. Without region/site here, a region or plant click leaves the key unchanged, so the component keeps
    # returning that SAME click on every later rerun. Combined with the
    # click handlers below now calling st.rerun() unconditionally, that
    # created a genuine infinite loop: click -> rerun -> same stale click
    # re-read -> rerun -> ... which is what was causing the "needs double
    # clicks / refreshes" symptom, especially once network latency (from
    # being deployed) widened the window for that loop to race real clicks.
    chart_key = (
        f"globe_{st.session_state.view}_{st.session_state.selected_country}_"
        f"{st.session_state.selected_sector}_{st.session_state.selected_region}_"
        f"{st.session_state.selected_site}_{bool(st.session_state.result_circle)}"
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
        # Clicked a region label -> select region, clear any single-plant selection.
        # Guarded (only act if this is actually a NEW region) so a stale replay
        # of the same click can't keep re-triggering st.rerun() forever.
        if 0 <= point_index < len(regions_names):
            new_region = regions_names[point_index]
            if new_region != st.session_state.selected_region:
                st.session_state.selected_region = new_region
                st.session_state.selected_site = None
                st.session_state.result_circle = None
                st.session_state.df_result = None
                st.rerun()
    
    elif st.session_state.view == "country" and curve_number == 3:
        # Clicked a plant marker -> select that single plant as the "site".
        # Same idempotency guard as the region branch above, for the same reason.
        if plants and 0 <= point_index < len(plants):
            new_site = plants[point_index]['name']
            if new_site != st.session_state.selected_site:
                st.session_state.selected_site = new_site
                st.session_state.selected_region = None
                st.session_state.result_circle = None
                st.session_state.df_result = None
                st.rerun()