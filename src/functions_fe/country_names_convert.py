import pycountry


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