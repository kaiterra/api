#!/usr/bin/env python3
#
# https://github.com/kaiterra/api/examples/restv1-urlkey.py
#
# This script demonstrates getting the latest data from a Laser Egg and Sensedge using the API.
#
# To use the script, do the following:
#  1. Use pip to install packages in requirements.txt (usually pip -r requirements.txt)
#  2. Change API_KEY to the key you created for your Kaiterra account on http://dashboard.kaiterra.com/.
#  3. Run the script.  It will make the request, printing out information about the auth process
#     along the way.

from datetime import datetime, timezone
import sys
import requests


API_BASE_URL = "https://api.kaiterra.com/v1/"

# TODO: replace this with the API key from your Kaiterra account
API_KEY = "your-api-key"

# Create a session object to reuse TCP connections to the server
session = requests.session()

def do_get(relative_url, *, params={}, headers={}):
    '''
    Executes an HTTP GET against the given resource.  The request is authorized using the given URL key.
    '''
    import json

    params['key'] = API_KEY

    url = API_BASE_URL.strip("/") + relative_url

    print("http: Fetching:   {}".format(url))
    print("http: Parameters: {}".format(params))
    print("http: Headers:  {}".format(headers))
    print()
    
    response = session.get(url, params=params, headers=headers)
    
    print("http: Status ({}), {} bytes returned:".format(response.status_code, len(response.content)))
    content_str = ''
    if len(response.content) > 0:
        content_str = response.content.decode('utf-8')
        print(content_str)
        print()

    response.raise_for_status()
        
    if len(content_str) > 0:
        return json.loads(content_str)

    return None


def get_laser_egg(id: str):
    return do_get("/lasereggs/" + id)


def get_sensedge(id: str):
    return do_get("/sensedges/" + id)


def summarize_laser_egg(id: str):
    '''
    Prints the most recently reported reading from a Laser Egg.
    '''
    data = get_laser_egg(id)

    latest_data = data.get('info.aqi')
    if latest_data:
        print("Laser Egg data returned:")

        ts = parse_rfc3339_utc(latest_data['ts'])
        ts_ago = (datetime.now(timezone.utc) - ts).total_seconds()
        print("  Updated: {} seconds ago".format(int(ts_ago)))

        pm25 = latest_data['data'].get('pm25')
        if pm25:
            print("  PM2.5:   {} µg/m³".format(pm25))
        else:
            print("  PM2.5:   no data")

    else:
        print("Laser Egg hasn't uploaded any data yet")

    print()


def summarize_sensedge(id: str):
    '''
    Prints the most recently reported reading from a Sensedge.
    '''
    data = get_sensedge(id)

    latest_data = data.get('latest')
    if latest_data:
        print("Sensedge data returned:")

        ts = parse_rfc3339_utc(latest_data['ts'])
        ts_ago = (datetime.now(timezone.utc) - ts).total_seconds()
        print("  Updated: {} seconds ago".format(int(ts_ago)))

        pm25 = latest_data.get('km100.rpm25c')
        if pm25:
            print("  PM2.5:   {} µg/m³".format(pm25))
        else:
            print("  PM2.5:   no data")

        tvoc = latest_data.get('km102.rtvoc (ppb)')
        if tvoc:
            print("  TVOC:    {} ppb".format(tvoc))
        else:
            print("  TVOC:    no data")

    else:
        print("Sensedge hasn't uploaded any data yet")

    print()


def check_available(name):
    import importlib
    try:
        _ = importlib.import_module(name, None)
    except ImportError:
        print("Missing module '{}'.  Please run this command and try again:".format(name))
        print("   pip -r requirements.txt")
        sys.exit(1)


def parse_rfc3339_utc(ts: str) -> datetime:
    '''
    Parses and returns the timestamp as a timezone-aware time in the UTC time zone.
    '''
    return datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)


if __name__ == "__main__":
    check_available("requests")
    from datetime import datetime, timezone

    summarize_laser_egg("00000000-0001-0001-0000-00007e57c0de")
    summarize_sensedge("00000000-0031-0001-0000-00007e57c0de")
