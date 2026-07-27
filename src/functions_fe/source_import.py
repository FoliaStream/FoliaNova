from requests.models import PreparedRequest
import requests


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