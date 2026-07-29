import pandas as pd

import os
import pycountry
import requests

from requests.models import PreparedRequest
import requests

# from src.functions_fe.helpers_functions import country_name_to_alpha3
from requests.models import PreparedRequest

def load_regions(country):

    regional_info = pd.read_csv(f"{os.getcwd()}/input/csv/regional_data.csv", index_col='Unnamed: 0')
    country_regions = [regional_info[regional_info['country']==country]]
    country_regions = pd.DataFrame(country_regions[0])

    regions_names = country_regions['subnational1'].unique().tolist()
    regions_lat = country_regions['lat'].unique().tolist()
    regions_lon = country_regions['lon'].unique().tolist()

    return regions_names, regions_lon, regions_lat




# Generate url for API query 
def request_url(url, params):
    
    request = PreparedRequest()
    request.prepare_url(url, params)

    return request.url


# Import source data from API
def source_import_api(url, params):

    # Merge url and params in url for query
    url_query = request_url(url, params)

    # Perform request
    response = requests.get(url_query)

    # if response == 200:
        # Success

    data = response.json()['assets']
    
    return data


def country_name_to_alpha3(name):
    try:
        return pycountry.countries.lookup(name).alpha_3
    except LookupError:
        return None 
    

def alpha3_to_country_name(alpha3):
    try:
        country = pycountry.countries.get(alpha_3=alpha3.upper())
        if country:
            return country.name
        else:
            return None
    except KeyError:
        return None


# Load source data
def load_source(country, years):
    """
    Fetches emissions data from ClimateTrace API for a country across specified years.
    Returns a DataFrame with emissions columns named by actual year (e.g., emissions_2024).
    
    Args:
        country (str): Country name (will be converted to Alpha-3 code)
        years (list): List of years (e.g., [2024, 2025, 2026])
    
    Returns:
        pd.DataFrame: Columns: [id, name, lat, lon, sector, emissions_2024, emissions_2025, ...]
    """
    country = country_name_to_alpha3(country)
    url = "https://api.climatetrace.org/v6/assets?"
    
    master_df = pd.DataFrame()
    asset_id_to_index = {}  # Maps asset IDs to DataFrame indices
    current_index = 0
    
    for year in sorted(years):  # Process years in order
        params = {
            'limit': 10000000000000,
            'gas': 'co2',
            'countries': country,
            'year': year
        }
        
        data = source_import_api(url, params)
        
        for asset in data:
            if asset['Id'] is None:
                continue
                
            asset_id = asset["Id"]
            
            # Add new asset to DataFrame if not already present
            if asset_id not in asset_id_to_index:
                master_df.at[current_index, 'id'] = asset_id
                master_df.at[current_index, 'name'] = asset["Name"]
                master_df.at[current_index, 'lat'] = float(asset['Centroid']['Geometry'][1])
                master_df.at[current_index, 'lon'] = float(asset['Centroid']['Geometry'][0])
                master_df.at[current_index, 'sector'] = str(asset['Sector'])
                asset_id_to_index[asset_id] = current_index
                current_index += 1
            
            # Add emissions for this year
            row_idx = asset_id_to_index[asset_id]
            emissions = float(asset['EmissionsSummary'][0]['EmissionsQuantity'])
            master_df.at[row_idx, f'emissions_{year}'] = emissions
    
    # Ensure consistent column order: metadata first, then emissions by year
    metadata_cols = ['id', 'name', 'lat', 'lon', 'sector']
    emission_cols = sorted([col for col in master_df.columns if col.startswith('emissions_')])
    master_df = master_df[metadata_cols + emission_cols]

    return master_df



# Generate url for API query 
def request_url(url, params):
    
    request = PreparedRequest()
    request.prepare_url(url, params)

    return request.url

# Import source data from API
def source_import_api(url, params):

    # Merge url and params in url for query
    url_query = request_url(url, params)

    # Perform request
    response = requests.get(url_query)

    # if response == 200:
        # Success

    data = response.json()['assets']
    
    return data




