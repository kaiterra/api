#!/usr/bin/env python3
#
# https://github.com/kaiterra/api/examples/restv1-auth.py
# This script demonstrates getting the latest data from a Laser Egg and Sensedge using the API.
#
# To use the script, do the following:
#  1. Use pip to install packages in requirements.txt (usually pip -r requirements.txt)
#  2. Change CLIENT_ID and HMAC_SECRET_KEY to the ID and key you were issued by Kaiterra.
#  3. Run the script.  It will make the request, printing out information about the auth process
#     along the way.

from datetime import datetime, timezone
import sys
import requests


API_BASE_URL = "https://api.kaiterra.cn/v1/"

# TODO: Replace this with your client ID and HMAC secret key
CLIENT_ID = "00000000001"
HMAC_SECRET_KEY = "your-hmac-secret-key"

# Create a session object to reuse TCP connections to the server
session = requests.session()

def hmac(key: bytes, message: bytes):
    import hashlib
    def hasher(msg: bytes = b''):
        return hashlib.sha256(msg)

    def hash(msg: bytes = b'') -> bytes:
        return hasher(msg).digest()

    blocksize = hasher().block_size

    # See https://en.wikipedia.org/wiki/Hash-based_message_authentication_code#Implementation
    if len(key) > blocksize:
        key = hash(key)

    if len(key) < blocksize:
        key = key + bytes(0 for _ in range(blocksize - len(key)))

    o_key_pad = bytes(0x5c ^ b for b in key)
    i_key_pad = bytes(0x36 ^ b for b in key)

    return hash(o_key_pad + hash(i_key_pad + message))


def auth_request_as_hmac(relative_url: str, params: dict=dict(), headers: dict=dict(), body: bytes=b'') -> (str, dict):
    """
    Given a desired HTTP request, returns the modified URL and request headers that are needed
    for the request to be accepted by the API.
    """
    import base64
    import time
    import collections
    import urllib.parse

    hex_key = bytearray.fromhex(HMAC_SECRET_KEY)

    print("Authenticating request using HMAC")
    print("Secret key: {}".format(bytes2hex(hex_key)))
    print()

    client_header = 'X-Kaiterra-Client'
    headers[client_header] = CLIENT_ID
    timestamp_header = 'X-Kaiterra-Time'
    headers[timestamp_header] = '{:x}'.format(int(time.time()))

    header_component = '{}={}&{}={}'.format(
        client_header, headers[client_header],
        timestamp_header, headers[timestamp_header]).encode('ascii')

    # Order doesn't matter
    relative_url_with_params = relative_url
    if params:
        relative_url_with_params += "?" + urllib.parse.urlencode(params)
    url_component = relative_url_with_params.encode('ascii')

    full_payload = header_component + url_component + body
    print("Full payload to be signed:")
    print(full_payload)
    print()

    headers['X-Kaiterra-HMAC'] = base64.b64encode(hmac(hex_key, full_payload))

    return (API_BASE_URL.strip("/") + relative_url_with_params, headers)


def bytes2hex(bb: bytes):
    return " ".join('%02x' % x for x in bb)


def do_req(verb, url, body=b'', params={}, headers={}):
    import requests
    import json

    (url, headers) = auth_request_as_hmac(url, body=body, params=params)

    if len(body) > 0:
        headers.update({'Content-Type': 'application/json'})

    print("Fetching: {}".format(url))
    print("Headers:  {}".format(headers))
    print()

    if verb == 'get':
        response = session.get(url, headers=headers)
    elif verb == 'post':
        response = session.post(url, body, headers=headers)
    elif verb == 'put':
        response = session.put(url, body, headers=headers)

    print("Status ({}), {} bytes returned:".format(response.status_code, len(response.content)))
    content_str = ''
    if len(response.content) > 0:
        content_str = response.content.decode('utf-8')
        print(content_str)

    response.raise_for_status()

    if len(content_str) > 0:
        return json.loads(content_str)

    return None


def get_laser_egg(id: str):
    return do_req('get', '/lasereggs/' + id)


def get_sensedge(id: str):
    return do_req('get', '/sensedges/' + id)


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
