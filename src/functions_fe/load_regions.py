import pandas as pd 
import numpy as np
import os

def load_regions(country):

    regional_info = pd.read_csv(f"{os.getcwd()}/input/csv/regional_data.csv", index_col='Unnamed: 0')
    country_regions = [regional_info[regional_info['country']==country]]
    country_regions = pd.DataFrame(country_regions[0])

    regions_names = country_regions['subnational1'].unique().tolist()
    regions_lat = country_regions['lat'].unique().tolist()
    regions_lon = country_regions['lon'].unique().tolist()

    return regions_names, regions_lon, regions_lat


    