import requests
import math 
import pycountry



# ////////////////////////////////////////////////
#                   FUNCTIONS II
# ////////////////////////////////////////////////


# Generate url for API query
def request_url(url, params):

    request = requests.models.PreparedRequest()
    request.prepare_url(url, params)

    return request.url


# Get source region 
def get_region(lat, lon, url, language):

    url_request = f"{url}lat={round(lat,6)}&lon={round(lon,6)}&format=json"
    headers = {
        "User-Agent":"FoliaNova (foliastream+folianova@gmail.com)",
        "Accept-Language":language
    }

    try:
        response = requests.get(url_request, headers=headers)
        response.raise_for_status()
        data = response.json()
        address = data.get('address',{})
        return address.get('state') or address.get('region') or address.get('county')
    
    except Exception as e:
        print(f"Error: {e}")
        return None


# Hectares to km radius
def hectares_to_circle_radius(area):

    area_km2 = area * 0.01
    radius_km = math.sqrt(area_km2 / math.pi)

    return radius_km




# Rename countries
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