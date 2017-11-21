#!/usr/bin/env python3
#
# https://github.com/kaiterra/api/examples/restv1-auth.py
# This script helps you verify that your client's HTTP requests to Kaiterra's public API
# are properly formed.
#
# Calls to Kaiterra's public API must be authenticated using one of two schemes:
#  - URL-based (developer key): the developer key is passed directly as a 'key' parameter 
#    in the request URL.  This is the simpler of the two auth schemes, and is suitable for
#    clients that will be running on trusted devices, such as a researcher's workstation,
#    or a server.
#  - HMAC-based scheme: the client signs the request with its secret key and passes the signature
#    in the request headers. Then, the server signs the request using the same secret key,
#    checks the signature, and thus verifies that the client is in possession of the secret key.
#    To prevent replays of captured requests, the current time is included in the signed payload.
#    This auth scheme is more complicated, but it makes it more difficult (though not impossible) to
#    extract the key from clients running on untrusted devices.
#
# To use the script, make the following changes:
#  - Change auth_method to represent the auth scheme used by your client.
#  - Change dev_demo_key or client_id and hmac_secret_key to the keys used by your client.
#  - Run the script.  It will make the request, printing out information about the auth process
#    along the way.


from datetime import datetime, timezone
import sys


base_url = "https://api.origins-china.cn/v1/"
# Controls the auth method used by this script.  Possible values are:
# - 'url': passes the developer key in the URL
# - 'hmac': uses the HMAC-based auth scheme in which the key itself does not appear in the network request
auth_method = "hmac"

# For "url" authentication:
# Developer key passed in the 'key' parameter in the URL.
# TODO: Replace this with your developer key, if you were issued one
dev_demo_key = "kOpAgVMnz2zM5l6XKQwv4JmUEvopnmUewFKXQ0Wvf9Su72a9"

# For "hmac" authentication:
# ID and secret key used to authorize requests  of your organization.  Required if using the "app" auth method.
# TODO: Replace this with your client ID and HMAC secret key, if you wre issued one
client_id = "2c13f157da77"
hmac_secret_key = "c92b4edcf25006c1854ab33144e4101261c419b48c6c5a2dbf3c349bd07b1f27c259632a2bf6812e15b994abb1dcffad160a495561986b04514bd5e070b985b1"


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
    
    hex_key = bytearray.fromhex(hmac_secret_key)
    
    print("Authenticating request using HMAC")
    print("Secret key: {}".format(bytes2hex(hex_key)))
    print("")

    client_header = 'X-Kaiterra-Client'
    headers[client_header] = client_id
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
    print("")

    headers['X-Kaiterra-HMAC'] = base64.b64encode(hmac(hex_key, full_payload))

    return (base_url.strip("/") + relative_url_with_params, headers)


def auth_request_as_url(relative_url: str, params: dict=dict(), headers: dict=dict(), body: bytes=b'') -> (str, dict):
    """
    Given a desired HTTP request, appends the developer key as a URL parameter.
    """
    import urllib.parse
    params['key'] = dev_demo_key

    return (base_url.strip("/") + relative_url + "?" + urllib.parse.urlencode(params), headers)


def do_req(verb, url, body=b'', params={}, headers={}):
    import requests
    import json
    if auth_method == "hmac":
        (url, headers) = auth_request_as_hmac(url, body=body, params=params)
    elif auth_method == "url":
        (url, headers) = auth_request_as_url(url, body=body, params=params)
    else:
        raise Exception("Unknown auth method '{}'".format(auth_method))

    if len(body) > 0:
        headers.update({'Content-Type': 'application/json'})
    
    print("Fetching: {}".format(url))
    print("Headers:  {}".format(headers))
    print("")
    
    if verb == 'get':
        response = requests.get(url, headers=headers, allow_redirects=False)
    elif verb == 'post':
        response = requests.post(url, body, headers=headers, allow_redirects=False)
    elif verb == 'put':
        response = requests.put(url, body, headers=headers, allow_redirects=False)

    print("Status ({}), {} bytes returned:".format(response.status_code, len(response.content)))
    content_str = ''
    if len(response.content) > 0:
        content_str = response.content.decode('utf-8')
        print(content_str)

    response.raise_for_status()
    if not (200 <= response.status_code < 300):
        raise Exception("Response code wasn't 2xx (was {})".format(response.status_code))
        
    if len(content_str) > 0:
        return json.loads(content_str)

    return None


def get_laser_egg(id: str):
    return do_req('get', id)


def bytes2hex(bb: bytes):
    return " ".join('%02x' % x for x in bb)


def check_available(name):
    import importlib
    try:
        _ = importlib.import_module(name, None)
    except ImportError:
        print("Missing module '{}'.  Please run this command and try again:".format(name))
        print("   pip -r requirements.txt")
        sys.exit(1)


if __name__ == "__main__":
    check_available("requests")
    
    data = get_laser_egg("/lasereggs/b55a2a78-d14d-4b27-9e20-91804925407d")
    
    print("Data returned:")
    print(data)

