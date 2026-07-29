import os
import yaml

import streamlit as st


from src.functions_fe.sidebar import setup_sidebar
from src.functions_fe.styles import HIDE_SIDEBAR_NAV


################
# --- SET UP ---
################

# --- PAGE CONFIG ---
st.set_page_config(page_title="FoliaNova - HOME", layout="wide")

# --- STYLES ---
st.markdown(HIDE_SIDEBAR_NAV, unsafe_allow_html=True)


# --- CONFIG ---
with open(f"{os.getcwd()}/src/config_fe/config.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)

# --- SIDEBAR & TITLE ---
selected_page = setup_sidebar(
    pages=config['pages'],
    main_page=config['main_page'])

    

# Navigation on click
if selected_page == "HOME":
    pass
elif selected_page == "SIMULATOR":
    st.switch_page("pages/SIMULATOR.py")
elif selected_page == "OVERVIEW":
    st.switch_page("pages/OVERVIEW.py")


# --- LOGO-TITLE ---
col1,col2,col3 = st.columns([1,2,1])
with col2:
    st.image(f"{os.getcwd()}/logo.png")

st.divider()


# --- DESCRIPTION ---
col1, col2 = st.columns([1,1])
with col1:
    st.header("Welcome to FoliaNova!")
    st.info("""
            This interactive web application evaluates and visualizes the carbon sequestration potential of reforestation efforts aimed at mitigating atmospheric CO₂ concentrations.

            Get started by exploring the pages!
            """)
    
with col2: 
    st.header("PAGES:")
    with st.expander("**🌍 OVERVIEW**"):
        st.subheader("Interactive Data Visualization")
        st.info("Select countries and visualize forestry data!")


        if st.button(label="EXPLORE", key='home_overview'):
            st.session_state.selected_page = "OVERVIEW"
            selected_page = "OVERVIEW"
            st.switch_page("pages/OVERVIEW.py")
                


    with st.expander("**🌿 SIMULATOR**"):
        st.subheader("Reforestation Modelling Tool")
        st.info("Combine forestry and industrial emissions data to evaluate reforestation potential!")

        if st.button(label="EXPLORE", key='home_simulator'):
            st.session_state.selected_page = "SIMULATOR"
            selected_page = "SIMULATOR"
            st.switch_page("pages/SIMULATOR.py")

        
st.divider()

# --- FOOTER ---
col1, col2, col3, col4 = st.columns([1,1,1,1])

with col1: 
    st.subheader("CONTACT")
with col2:
    st.markdown("**Mail**")
    st.markdown("📩 foliastream+folianova@gmail.com")
with col3:
    st.markdown("**Link**")
    st.caption("🌐 https://folianova.streamlit.app")
with col4: 
    st.markdown("**GitHub**")
    st.caption("</>  https://github.com/FoliaStream/FoliaNova")


st.caption("© 2026 FoliaNova - Carbon Sequestration Analysis Tool")
