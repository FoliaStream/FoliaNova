

import streamlit as st
import plotly.graph_objects as go 
import numpy as np
import pandas as pd 
import plotly.express as px

import os
import yaml 
import folium

from streamlit_plotly_events import plotly_events
from src.functions_fe.sidebar import setup_sidebar
from src.functions_fe.styles import HIDE_SIDEBAR_NAV, METRICS_BOX_STYLE
from src.functions_fe.helpers_functions import country_name_to_alpha3, load_source
from src.functions_fe.overview_functions import forest_metrics, detect_deforestation_hotspots, carbon_forecast, get_annual_emissions



################
# --- SET UP ---
################

# --- PAGE CONFIG --- 
st.set_page_config(page_title="FoliaNova - OVERVIEW", layout="wide")

# --- STYLES ---
st.markdown(HIDE_SIDEBAR_NAV, unsafe_allow_html=True)
st.markdown(METRICS_BOX_STYLE, unsafe_allow_html=True)

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
    st.switch_page("pages/SIMULATOR.py")
elif selected_page == "OVERVIEW":
    pass


# --- LOGO-TITLE ---
col1,col2,col3 = st.columns([1,2,1])
with col2:
    st.image(f"{os.getcwd()}/LOGO.png")

st.divider()

# 
# --- HEADER ---
st.title("🌍 OVERVIEW")
st.header("Select country:")
st.markdown('#')


# Create figure
highlighted_countries_names = config['countries']
highlighted_countries_codes = [country_name_to_alpha3(country) for country in config['countries']]

# Colors
HIGHLIGHT_COLOR = "rgba(0, 255, 0, 0.5)"      
BORDER_COLOR = "rgb(0, 80, 200)"          
BACKGROUND_COLOR = "rgb(245, 248, 250)"   
OCEAN_COLOR = "rgb(220, 235, 255)"    

# Globe
globe = go.Figure()


# Hover texts
hover_texts = []
for country in highlighted_countries_names:
    hover_texts.append(f"<span style='font-size: 20px;'>{country}</span><b></b><br>")


# Add highlighted countries
globe.add_trace(go.Choropleth(
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


globe.update_layout(
    geo=dict(
        showland=True,
        landcolor='rgb(245, 248, 250)',
        showocean=True,
        oceancolor='rgb(220, 235, 255)',
        showcountries=True,
        countrycolor='rgba(0, 80, 200, 0.4)',
        countrywidth = 1.5,
        showcoastlines=True,
        coastlinecolor='rgb(0, 80, 200)',
        projection=dict(
            type='orthographic',
            scale=0.9,
            rotation=dict(lon=50, lat=21, roll=0)),
        bgcolor='rgba(0, 0, 0, 0)',
        showframe=False,
        lataxis=dict(showgrid=False),
        lonaxis=dict(showgrid=False),
    ),
    paper_bgcolor='rgba(0, 0, 0, 0)',
    plot_bgcolor='rgba(0, 0, 0, 0)',
    margin=dict(l=0, r=0, t=0, b=0),
    # width=800,
    dragmode='pan',
    autosize=True
)



selected_points = plotly_events(
    globe, 
    click_event=True,
    select_event=False,
    hover_event=False,
    override_height=800,  
    key="globe",
)


if selected_points:
    clicked_point = selected_points[0]
    country_index = clicked_point.get('pointIndex', 0)
    selected_country = highlighted_countries_names[country_index]
    
    st.markdown(f"<h1 style='text-align: center;'>{selected_country}</h1>", unsafe_allow_html=True)
    st.divider()

    with st.spinner("Work in progress..."):
            
        if selected_country in highlighted_countries_names:

            # Side-by-side layout
            col1, col2 = st.columns([1, 1])

            with col1:
                st.header("**🏭 POLLUTERS**")
            with col2: 
                st.header("**🌿 FORESTS**")

            # EMITTERS
            with col1:

                options_year = [2021, 2022, 2023, 2024]
                selected_year = st.selectbox('Reference Year', options=options_year, index=3)

                # Filter out zero-emission sites before any calculations
                df_source = load_source(selected_country, [selected_year])
                df_source = df_source[df_source[f'emissions_{selected_year}'] > 0]  # THIS IS THE KEY FILTER

                # Metrics (now only counting sites with emissions)
                st.metric(f"Total number of emitting sites in {selected_country}", f"{int(len(df_source)):,}")
                st.metric(f"Total emissions in {selected_country}", f"{int(sum(df_source[f'emissions_{selected_year}'])/1000000):,} Mt")
                
                # Pie chart - Sectors (only for sectors with emissions)
                sector_counts = df_source['sector'].value_counts()

                # Group small sectors into "Others"
                threshold = 10
                main_sectors = sector_counts[sector_counts >= threshold]
                other_sectors = sector_counts[sector_counts < threshold]

                if len(other_sectors) > 0:
                    sectors_list = main_sectors.index.tolist() + ['Others']
                    sectors_count = main_sectors.tolist() + [other_sectors.sum()]
                else:
                    sectors_list = main_sectors.index.tolist()
                    sectors_count = main_sectors.tolist()

                # Create the pie chart
                sectors_pie = go.Figure(data=[go.Pie(
                    labels=sectors_list,
                    values=sectors_count,
                    hole=.6,
                    hoverinfo='label+percent+value',
                    textinfo='value'
                )])

                sectors_pie.update_layout(
                    title=f"Industrial Sites per Sector ({selected_year})",
                    showlegend=True,
                    margin=dict(t=50, b=0, l=0, r=0)
                )

                st.markdown('###')
                st.plotly_chart(sectors_pie, use_container_width=True)


                # Line graph --> time x emissions x sector
                df_source_all_year = load_source(selected_country, options_year)
                
                plot_data = []
                for year in options_year:
                    year_col = f'emissions_{year}'
                    year_df = df_source_all_year[['sector', year_col]].copy()
                    year_df['year'] = year
                    year_df = year_df.rename(columns={year_col: 'emissions'})
                    year_df = year_df.groupby(['sector', 'year'])['emissions'].sum().reset_index()
                    plot_data.append(year_df)

                plot_df = pd.concat(plot_data)
                plot_df = plot_df[plot_df['emissions'] > 0]

                fig = px.area(
                    plot_df,
                    x='year',
                    y='emissions',
                    color='sector',
                    title='CO₂ Emissions by Sector',
                    labels={'emissions': 'Emissions (metric tons)'},
                    category_orders={"year": [2021, 2022, 2023, 2024]},
                    hover_data={
                        'year': True,
                        'sector': True,
                        'emissions': ':.1f'  # Format with 1 decimal place
                    }
                )

                # 4. Customize tooltip appearance
                fig.update_traces(
                    hovertemplate=(
                        "<b>%{fullData.name}</b><br>"  
                        "Year: %{x}<br>"               
                        "Emissions: %{y:,.1f} tons<br>"  
                        "<extra></extra>"              
                    )
                )
        
                fig.update_xaxes(
                                type='category',
                                tickmode='array',
                                tickvals=options_year,
                                ticktext=options_year
                            )

                st.plotly_chart(fig, use_container_width=True)

            # FOREST  
            with col2: 

                df_forest = pd.read_csv(config['forest_path'])
                country_forest = df_forest[df_forest['country'] == selected_country].copy()

                if not country_forest.empty:
                    metrics = forest_metrics(country_forest)

                    # Area and Carbon Stock
                    m1, m2 = st.columns(2)
                    m1.metric("🌳 Forest Area", f"{metrics['total_area']/1e6:,.1f} M ha")
                    m2.metric("💚 Carbon Stock", f"{metrics['total_carbon']/1e6:,.1f} M ha")

                    # Net Flux
                    m3, m4 = st.columns(2)
                    m3.metric("📊 Net Flux", f"{metrics['net_flux']/1e6:,.2f} Mt CO₂e/yr", 
                            "Sink 🌱" if metrics['net_flux'] < 0 else "Source 🔥")
                    m4.metric("📍 Regions", f"{metrics['n_regions']}")
                    
                    st.divider()

                    t1, t2, t3 = st.tabs(["📈 Timeline", "🗺️ Hotspots", "🔮 Forecast"])

                    # Emissions timeline
                    with t1:
                        years, annual = get_annual_emissions(country_forest)
                         
                        if years and annual: 
                            # Convert to MT
                            annual_mt = [a/1e6 for a in annual]

                            # Sort by year
                            sorted_data = sorted(zip(years, annual_mt))
                            years_sorted, annual_sorted = zip(*sorted_data)

                            fig = go.Figure()
                            fig.add_trace(go.Bar(x=years_sorted, y=annual_sorted, name='Emissions', marker_color='#FF6B6B'))
                            fig.add_trace(go.Scatter(x=years_sorted, y=pd.Series(annual_sorted).rolling(3, min_periods=1).mean(), 
                                                    name='3Y Avg', line=dict(color='#2C3E50', width=2)))
                            fig.update_layout(title=f"CO₂ from Forest Loss", height=500,
                                            xaxis_title="Year", yaxis_title="Mt CO₂e")
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Stats
                            c1, c2 = st.columns(2)
                            c1.metric("Avg Annual", f"{np.mean(annual_sorted):.2f} Mt")
                            c2.metric("Peak", f"{max(annual_sorted):.2f} Mt ({years_sorted[np.argmax(annual_sorted)]})")
                            c3,c4 = st.columns([2,1])
                            c3.metric("Trend", "📈 Increasing" if metrics.get('emissions_increasing', False) else "📉 Decreasing",
                                    help=f"p-value: {metrics.get('trend_p_value', 'N/A'):.3f}" if metrics.get('trend_significant', False) else "Not significant")
                            
                            st.divider()
                            col1, col2 = st.columns(2)
                            
                            # 1. Total cumulative emissions
                            total_cumulative = sum(annual_sorted)
                            col1.metric("📊 Cumulative Total", f"{total_cumulative:.2f} Mt CO₂e",
                                    help="Total emissions from 2001 to 2024")
                            
                            # 2. Emissions intensity (per hectare)
                            emissions_per_ha = metrics['total_emissions'] / metrics['total_area'] if metrics['total_area'] > 0 else 0
                            col2.metric("📏 Emissions/ha", f"{emissions_per_ha:.2f} t CO₂e/ha/yr",
                                    help="Average emissions per hectare of forest")
                        else:
                            st.warning("No valid emission data available")
                    
                    with t2:
                        hotspots = detect_deforestation_hotspots(country_forest)
                        
                        if not hotspots.empty:
                            fig = go.Figure()
                            fig.add_trace(go.Bar(y=hotspots['subnational1'], x=hotspots['pressure_score'],
                                                orientation='h', marker_color='#FF4444',
                                                text=hotspots['pressure_score'].round(2), textposition='outside'))
                            fig.update_layout(title=f"Top Deforestation Hotspots", height=700,
                                            xaxis_title="Carbon Loss Rate (%/yr)", yaxis_title="Region")
                            st.plotly_chart(fig, use_container_width=True)
                            st.divider()
                            col1, col2, col3 = st.columns(3)
                            
                            # 1. Highest loss rate
                            highest_loss = hotspots.iloc[0]['pressure_score']
                            highest_region = hotspots.iloc[0]['subnational1']
                            col1.metric("🔥 Highest Loss Rate", f"{highest_loss:.2f}%/yr",
                                    help=f"{highest_region} is losing carbon fastest")
                            
                            # 2. Average loss rate of top 5
                            avg_loss_top5 = hotspots['pressure_score'].head(5).mean()
                            col2.metric("📊 Top 5 Avg Loss", f"{avg_loss_top5:.2f}%/yr",
                                    help="Average loss rate of top 5 hotspots")
                            
                            # 3. Total emissions from hotspots
                            hotspots_emissions = hotspots['gfw_forest_carbon_gross_emissions__Mg_CO2e_yr-1'].sum()
                            total_emissions = country_forest['gfw_forest_carbon_gross_emissions__Mg_CO2e_yr-1'].sum()
                            pct_contribution = (hotspots_emissions / total_emissions * 100) if total_emissions > 0 else 0
                            col3.metric("🎯 Hotspots Share", f"{pct_contribution:.1f}%",
                                    help="% of total emissions from top 5 hotspots")
                            
                        else:
                            st.info("No hotspots detected")
                        
                    
                    with t3:
                        
                        forecast = carbon_forecast(country_forest)
                        if forecast is not None and not forecast.empty:
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=forecast['year'], y=forecast['forecast_emissions']/1e6,
                                                    mode='lines+markers', name='Forecast',
                                                    line=dict(color='#4A90E2', width=3)))
                            if 'confidence_interval' in forecast.columns:
                                fig.add_trace(go.Scatter(x=forecast['year'], 
                                                        y=(forecast['forecast_emissions'] + forecast['confidence_interval'])/1e6,
                                                        mode='lines', line=dict(dash='dash', color='gray'),
                                                        name='Upper CI', showlegend=False))
                                fig.add_trace(go.Scatter(x=forecast['year'],
                                                        y=(forecast['forecast_emissions'] - forecast['confidence_interval'])/1e6,
                                                        mode='lines', line=dict(dash='dash', color='gray'),
                                                        name='Lower CI', showlegend=False,
                                                        fill='tonexty', fillcolor='rgba(74,144,226,0.2)'))
                            fig.update_layout(title=f"5-Year Forecast", height=650,
                                            xaxis_title="Year", yaxis_title="Mt CO₂e")
                            st.plotly_chart(fig, use_container_width=True)
                            st.caption(f"📌 Projected {forecast['year'].iloc[-1]}: {forecast['forecast_emissions'].iloc[-1]/1e6:.2f} Mt CO₂e")
                            st.divider()
                            col1, col2, col3 = st.columns(3)
                            
                            # Trend direction
                            slope, intercept = np.polyfit(forecast['year'], forecast['forecast_emissions'], 1)
                            trend = "📈 Increasing" if slope > 0 else "📉 Decreasing"
                            col1.metric("🔮 Trend Direction", trend,
                                    help=f"Emissions are {'rising' if slope > 0 else 'falling'} by {abs(slope/1e6):.2f} Mt/year")
                            
                            # Forecast reliability
                            if 'confidence_interval' in forecast.columns:
                                ci_width = forecast['confidence_interval'].iloc[-1] / forecast['forecast_emissions'].iloc[-1] * 100
                                reliability = "🟢 High" if ci_width < 20 else "🟡 Medium" if ci_width < 40 else "🔴 Low"
                                col2.metric("🎯 Forecast Reliability", reliability,
                                        help=f"Confidence interval width: {ci_width:.1f}% of projection")
                            else:
                                col2.metric("🎯 Forecast Reliability", "N/A")
                            
                            
                            # Average annual change
                            col3.metric("📊 Annual Change Rate", f"{slope/1e6:+.2f} Mt/year",
                                    help="Average change in emissions per year")
                            
                            st.caption(f"📌 Projected {forecast['year'].iloc[-1]}: {forecast['forecast_emissions'].iloc[-1]/1e6:.2f} Mt CO₂e")
                        else:
                            st.info("Insufficient data for forecasting")

                    






                    # # =========================
                    # # --- REGIONAL ANALYSIS ---
                    # # =========================
                    
                    # # Prepare regional data
                    # regional_df = country_forest.copy()
                    
                    # regional_analysis = regional_df.groupby('subnational1').agg({
                    #     'umd_tree_cover_extent_2000__ha': 'sum',
                    #     'gfw_aboveground_carbon_stocks_2000__Mg_C': 'sum',
                    #     'gfw_forest_carbon_gross_emissions__Mg_CO2e_yr-1': 'sum',
                    #     'gfw_forest_carbon_gross_removals__Mg_CO2_yr-1': 'sum',
                    #     'gfw_forest_carbon_net_flux__Mg_CO2e_yr-1': 'sum'
                    # }).reset_index()
                    
                    # # Calculate derived metrics
                    # regional_analysis['carbon_density'] = regional_analysis['gfw_aboveground_carbon_stocks_2000__Mg_C'] / regional_analysis['umd_tree_cover_extent_2000__ha']
                    # regional_analysis['emissions_intensity'] = regional_analysis['gfw_forest_carbon_gross_emissions__Mg_CO2e_yr-1'] / regional_analysis['umd_tree_cover_extent_2000__ha']
                    # regional_analysis['loss_rate'] = (regional_analysis['gfw_forest_carbon_gross_emissions__Mg_CO2e_yr-1'] / regional_analysis['gfw_aboveground_carbon_stocks_2000__Mg_C']) * 100
                    # regional_analysis['is_sink'] = regional_analysis['gfw_forest_carbon_net_flux__Mg_CO2e_yr-1'] < 0
                    # regional_analysis['removal_efficiency'] = (regional_analysis['gfw_forest_carbon_gross_removals__Mg_CO2_yr-1'] / regional_analysis['gfw_forest_carbon_gross_emissions__Mg_CO2e_yr-1']) * 100
                    # regional_analysis['removal_efficiency'] = regional_analysis['removal_efficiency'].replace([np.inf, -np.inf], 0).fillna(0)
                    
                    # # Replace inf/NaN
                    # regional_analysis = regional_analysis.replace([np.inf, -np.inf], 0).fillna(0)
                    
                    # # Sort by loss_rate (highest first)
                    # regional_analysis = regional_analysis.sort_values('loss_rate', ascending=False)

            # # MAP FORESTRY
            # st.divider()
            # st.subheader("Regional Forest Map")
            # st.write(selected_country)

            # regional_map = st.pydeck_chart()