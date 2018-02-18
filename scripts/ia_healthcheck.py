import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
import os
import random
import sys

MAX_CAPTURE_AGE = timedelta(hours=72)
LINKS_TO_CHECK = 5
SCANNER_USER = os.environ['SCANNER_USER']
SCANNER_PASSWORD = os.environ['SCANNER_PASSWORD']

def query_webmondb():
    """
    Set user and pass as environmental variables from command line
    For MacOS: in the terminal:
    export SCANNER_USER="your API user name"
    export SCANNER_PASSWORD="your API password"
    Query the web monitoring API to get random links
    Integer -> List
    """
    api = 'https://api.monitoring.envirodatagov.org/api/v0/pages?chunk_size=1'
    try:
        response = requests.get(api, auth=HTTPBasicAuth(SCANNER_USER, SCANNER_PASSWORD))
    except Exception as e:
        print('Could not access Scanner API')
        print(e)
        return []
    else:    
        response = response.json()
        url_count = response['meta']['total_results']
        links = [query_webmondb_url(number) for number in random.sample(range(url_count),LINKS_TO_CHECK)]
        return links

def query_webmondb_url(number):
    """
    Take an integer and query the web-mon-api to retreive a url based on n urls.
    The integer is the chunk number of chunk_size of 1.   
    Int -> Str
    """
    api = 'https://api.monitoring.envirodatagov.org/api/v0/pages?chunk='+str(number)+'&chunk_size=1'
    try:
        response = requests.get(api, auth=HTTPBasicAuth(SCANNER_USER, SCANNER_PASSWORD))
    except Exception as e:
        print('Could not access Scanner API with link: %d' % number)
        print(e)
        return None
    else:
        response = response.json()
        return response['data'][0]['url']     

def query_wayback(url):
    """
    Query Wayback Machine
    String -> JSON Object
    """ 
    url = 'http://archive.org/wayback/available?url=%s' % url
    try:
        response = requests.get(url)
    except:
        print("Could not access Wayback API")
    else:
        response = response.json()
        return response


def get_time(response):
    """
    Get the timestamp from the Wayback URL JSON Object
    Convert Wayback time to datetime object
    JSON Object -> DateTime Object
    """
    try:
        time = response['archived_snapshots']['closest']['timestamp']
    except KeyError:
    	print("Could not unpack response")
    	print(response)
    	return None

    else:
    	return datetime.strptime(time, '%Y%m%d%H%M%S')

def check_time(time_limit, response):
    """
    Check to see latest time is within the time limit
    Int, DateTime -> Boolean
    """
    time = get_time(response)
    if not time:
        status = False
    else:
        status = (datetime.now() - time)  < time_limit
    return {'Status': status, 'Response': response, 'Current Time': datetime.now(), 'Last Capture': time}

def is_healthy(responses):
    """
    Take Respones from Wayback and determine if the IA has recent snapshots
    Dict -> None
    """
    link_health = [check_time(MAX_CAPTURE_AGE, response) for response in responses]
    output_file(link_health)
    return	

def output_file(responses):
    """
    Write Output to a Text file
    List -> None
    """
    fileoutput = open("ia_healthcheck.txt", "w")
    healthy_links = 0
    unhealthy_links = 0
    
    if not responses:
        fileoutput.write('No links were returned.')
    else:    
        for url in responses:
            fileoutput.write(str(url)+'\n\n\n')		
            if url['Status'] == True:
                healthy_links += 1
            else: unhealthy_links +=1
        fileoutput.write('Found: {} Healthy Links and {} Unhealthy Links.'.format(healthy_links,unhealthy_links))	
    fileoutput.close()
    return


def output_email():
    """
    Send Output to and Email
    List -> None
    """
    return

# Get the random list of links from the Web Monitoring DB
# Get the responses of the links from the Wayback URL
# Check to see if the responses are within the time limit and write the output
if __name__ == "__main__":
    links = query_webmondb()
    responses = [query_wayback(url) for url in links if url]
    is_healthy(responses)




