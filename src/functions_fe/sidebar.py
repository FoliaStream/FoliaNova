import streamlit as st
from streamlit_option_menu import option_menu
from src.functions_fe.styles import SIDEBAR_STYLES
import os

# SIDEBAR
def setup_sidebar(pages,
                  main_page):
    with st.sidebar:
        col1, col2, col3 = st.columns([0.2, 0.7, 0.2])
        st.image(f"{os.getcwd()}/logo.png")
        
        # Initialize session state for page if it doesn't exist
        if 'selected_page' not in st.session_state:
            st.session_state.selected_page = main_page
        
        choose = option_menu("", 
                            pages,
                            default_index=pages.index(st.session_state.selected_page),
                            styles=SIDEBAR_STYLES)
        
        if choose != st.session_state.selected_page:
            st.session_state.selected_page = choose
            st.rerun()  
        
        st.divider()
        st.subheader("DATA SOURCES:")
        st.link_button("Climate TRACE", "https://climatetrace.org/", use_container_width=True)
        st.link_button("Global Forest Watch", "https://www.globalforestwatch.org", use_container_width=True)
    
    return st.session_state.selected_page
