import os 
import shutil
import errno
import requests
import time

from loguru import logger
from functions.functions_II import request_url, get_region, hectares_to_circle_radius

import pandas as pd 

# //////////////////////////////////////////////////////
#                  FUNCTIONS I LEVEL
# //////////////////////////////////////////////////////

#----------------------
# STEP . Base folders
#----------------------

def setup_dir(path: str):

    # Already existing -> Delete & Create new 
    if os.path.exists(path):
        shutil.rmtree(path)
        try: 
            logger.info(f"Create folder: {path}")
            os.makedirs(path)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
    
    # Not existing -> Create new
    else: 
        try: 
            logger.info(f"Create folder: {path}")
            os.makedirs(path)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise

    return path

#----------------------
# STEP . Case folders
#----------------------

def create_folder(path):

    # Check exist
    if not os.path.exists(path):
        #Create folder
        try:
            logger.info(f"Create folder: {path}")
            os.makedirs(path)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
    return path


#----------------------
# STEP . Source load
#----------------------

# Get data from API
def source_import_api(url, params):

    # Merge url and params in url for query
    url_query = request_url(url, params)

    # Perform request
    response = requests.get(url_query)

    # if response == 200 
    #   Success
    data = response.json()['assets']

    return data


# Format API data
def source_edit(source, id_col, emit_col, lat_col, lon_col, name_col, url_region_api, language_region_api, country, region, site, country_col, region_col):

    df_source = pd.DataFrame()

    # Convert source to dataframe
    for i in range(len(source)):
        if source[i]['Id'] is not None:
            df_source.at[i,id_col] = source[i]['Id']
            df_source.at[i,name_col] = source[i]['Name']
            df_source.at[i,emit_col] = float(source[i]['EmissionsSummary'][0]['EmissionsQuantity'])
            df_source.at[i,lat_col] = float(source[i]['Centroid']['Geometry'][1])
            df_source.at[i,lon_col] = float(source[i]['Centroid']['Geometry'][0])

    # Filter
    df_source[id_col] = df_source[id_col].astype(int)
    df_source = df_source[df_source[emit_col] > 0]
    
    # Country level dataframe
    df_source_country = pd.DataFrame(df_source)
    df_source_country[country_col] = country

    # Region level dataframe
    if region != 'None':
    # Get region of each source
        df_source[region_col] = pd.Series()
        for i, row in df_source.iterrows():
            time.sleep(1)
            df_source.at[i, region_col] = get_region(row[lat_col], row[lon_col], url_region_api, language_region_api)
        df_source_region = df_source[df_source[region_col].str.contains(region, case=False, na=False)]
    else:
        df_source_region = pd.DataFrame()

    # Site level dataframe
    if site != 'None':
    # Get region of single source
        df_source_site = df_source[df_source[name_col].str.contains(site, case=False, na=False)]
        df_source_site[region_col] = pd.Series()
        for i, row in df_source_site.iterrows():
            time.sleep(1)
            df_source_site.at[i, region_col] = get_region(row[lat_col], row[lon_col], url_region_api, language_region_api)
    else:
        df_source_site = pd.DataFrame() 


    return df_source_country, df_source_region, df_source_site


#----------------------
# STEP . Sink load
#----------------------

# Import csv data
def csv_import(path):

    df = pd.read_csv(path)

    return df


# Edit sink data
def sink_edit(sink, country, region, site, threshold, country_col, region_col, site_col, cover_col, intake_col, efficiency_col, threshold_col, site_region, country_efficiency_col):

    sink_out = pd.DataFrame(sink)

    # Filter threshold
    sink_out = sink_out[sink_out[threshold_col] == threshold]

    # Extract columns
    sink_out = sink_out[[country_col, region_col, threshold_col, cover_col,  intake_col]]


    # Sink hectar effifiency compute
    sink_out[efficiency_col] = sink_out[intake_col]/sink_out[cover_col]
    sink_out[country_efficiency_col] = sink_out[intake_col].sum()/sink_out[cover_col].sum() # so wrong... 


    # Filter area
    if country != 'None':
        sink_out_country = sink_out[sink_out[country_col] == country]

    else:
        sink_out_country = pd.DataFrame()

    if region != 'None':
        sink_out_region = sink_out[sink_out[region_col] == region]
    else:
        sink_out_region = pd.DataFrame()

    if site != 'None':
        if region != 'None':
            sink_out_site = pd.DataFrame(sink_out_region)
            sink_out_site[site_col] = site 
        else:
            sink_out_site = pd.DataFrame(sink_out)
            sink_out_site = sink_out_site[sink_out_site[region_col].apply(lambda x: x in site_region)]
            sink_out_site[site_col] = site     
    else:
        sink_out_site = pd.DataFrame()  


    return sink_out_country, sink_out_region, sink_out_site



#---------------------------
# STEP . Forest calculation
#---------------------------

def forest_calculation(source_country, source_region, source_site, country, region, site, sink_country, sink_region, sink_site, source_emissision_col, sink_region_efficiency_col, sink_country_efficiency_col):

    if country != 'None':
        out_country = pd.DataFrame(source_country)
        out_country['new_forest'] = pd.Series()
        out_country['new_area_radius'] = pd.Series()

        for i, row in out_country.iterrows():
            out_country.at[i,'new_forest'] = row[source_emissision_col] / abs(sink_country[sink_country_efficiency_col].iloc[0])

        for i, row in out_country.iterrows():
            out_country.at[i,'new_area_radius'] = hectares_to_circle_radius(row['new_forest'])
    else:
        out_country = pd.DataFrame()
    

    if region != 'None':
        out_region = pd.DataFrame(source_region)
        out_region['new_forest'] = pd.Series()
        out_region['new_area_radius'] = pd.Series()

        for i, row in out_region.iterrows():
            out_region.at[i,'new_forest'] = row[source_emissision_col] / abs(sink_region[sink_region_efficiency_col].iloc[0])
        
        for i, row in out_region.iterrows():
            out_region.at[i,'new_area_radius'] = hectares_to_circle_radius(row['new_forest'])
    else:
        out_region = pd.DataFrame()
        

    if site != 'None':
        out_site = pd.DataFrame(source_site)
        out_site['new_forest'] = pd.Series()
        out_site['new_area_radius'] = pd.Series()

        for i, row in out_site.iterrows():
            out_site.at[i,'new_forest'] = row[source_emissision_col] / abs(sink_site[sink_region_efficiency_col].iloc[0])

        for i, row in out_site.iterrows():
            out_site.at[i,'new_area_radius'] = hectares_to_circle_radius(row['new_forest'])
    else:
        out_site = pd.DataFrame()

    return out_country, out_region, out_site