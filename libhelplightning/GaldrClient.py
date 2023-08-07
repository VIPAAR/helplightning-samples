#!/usr/bin/env python3
#
# This script fetches all the calls and details
#  and writes them to the analytics db.

import requests
import json
import csv
import urllib.parse
import http.server
import webbrowser
import base64
import hashlib
import os
import webbrowser
import getpass
import sys

OAUTH_REDIRECT_PORT = 56824
OAUTH_REDIRECT_PATH = '/callback'

class GaldrClient:
    def __init__(self, logger, url, api_key, username=None, password=None, token=None, refreshToken=None):
        self.lg = logger
        self.url = url
        self.base_url = self._get_base_url(url)
        self.api_key = api_key
        if token is not None:
            self.token = token
        elif refreshToken is not None:
            self.token = self.refresh_token(refreshToken)
        elif username is not None:
            r = self._federate(username)
            auth_provider = r['type']
            if auth_provider == 'password':
                if password is not None:
                    self.token = self.auth_password(username, password)
                else:
                    self.password = getpass.getpass()
                    self.token = self.auth_password(username, self.password)
            elif auth_provider == 'oauth2':
                self.token = self._oauth2_flow(r['oauth2'])
            else:
                self.lg.error(f'GaldrClient: unknown auth type for user {username}')
        else:
            self.lg.error('GaldrClient: no valid authentication credentials provided')

    def _get_base_url(self, url):
        parts = urllib.parse.urlsplit(url)
        base_parts = [parts.scheme, parts.hostname, '', '', '']
        return urllib.parse.urlunsplit(base_parts)

    ###########################
    # START Auth Methods
    ###########################
    def _federate(self, username):
        headers = {
            'x-helplightning-api-key': self.api_key,
            'Content-Type': 'application/json'
        }
        body = {
            'email': username
        }
        r = requests.post(
            self.base_url + '/auth/federate',
            data=json.dumps(body),
            headers=headers
        )
        r.raise_for_status()
        return r.json()

    def auth_password(self, username, password):
        body = {
            'email': username,
            'password': password
        }
        data = self.post_no_token('/v1r1/auth', body)
        return data['token']

    def _oauth2_flow(self, oauth2_params):
        k = hashlib.sha256(os.urandom(1024)).hexdigest()
        state = {'redirect_uri': f'http://localhost:{OAUTH_REDIRECT_PORT}{OAUTH_REDIRECT_PATH}', 'k': k}
        b64_state = base64.urlsafe_b64encode(json.dumps(state).encode('UTF-8')).decode('UTF-8')
        params = {'state': b64_state}
        if oauth2_params.get('parameters', {}).get('login_hint', None):
            params['login_hint'] = oauth2_params['email']

        cb_server = CallbackServer('localhost', OAUTH_REDIRECT_PORT, b64_state, OAuthCallbackHandler)

        webbrowser.open(oauth2_params['url'] + '?' + urllib.parse.urlencode(params))
        print(oauth2_params['url'] + '?' + urllib.parse.urlencode(params), file = sys.stderr)
        cb_server.handle_request()
        return cb_server.token
    
    def set_token(self, token):
        self.token = token

    def refresh_token(self, token):
        body = {
            'refresh_token': token
        }
        data = self.post_no_token('/v1/auth/refresh', body)
        return data['token']
    ###########################
    # END Auth Methods
    ###########################

    ###########################
    # START Pagination Methods
    ###########################
    def get_all(self, path, data={}, extra_headers={}, page_size=50):
        """
        Paginates through server data until
        all records are fetched.
        """
        page = 1
        resp = self.get(
            path + '?page={}&page_size={}'.format(page, page_size),
            data,
            extra_headers
        )
        entries = resp.get('entries')
        while resp['total_entries'] > page * page_size:
            page += 1
            resp = self.get(
                path + '?page={}&page_size={}'.format(page, page_size),
                data,
                extra_headers
            )
            entries = entries + resp.get('entries')
        return entries

    def get_all_cb(self, callback, path, data={}, extra_headers={}, page_size=50):
        """
        Paginates through server data until
        all records are fetched, but calls the callback
        function with the results for each page.
        """
        results = []
        
        page = 1
        resp = self.get(
            path + '?page={}&page_size={}'.format(page, page_size),
            data,
            extra_headers
        )
        entries = resp.get('entries')
        results.extend(callback(entries))
        while resp.get('total_entries', 0) > page * page_size:
            try:
                resp = self.get(
                    path + '?page={}&page_size={}'.format(page+1, page_size),
                    data,
                    extra_headers
                )
                entries = resp.get('entries')
                results.extend(callback(entries))
                page += 1
            except requests.exceptions.RequestException as e:
                # retry
                print('Error making request', e)
                print('Retrying...')
                pass

        return results
    
    ###########################
    # END Pagination Methods
    ###########################

    ###########################
    # START HTTP methods
    ###########################
    def get(self, path, data={}, extra_headers={}):
        self.lg.debug('GET {}'.format(path))
        headers = {
            'x-helplightning-api-key': self.api_key,
            'Authorization': self.token,
            'Content-Type': 'application/json'
        }
        headers.update(extra_headers)
        r = requests.get(
            self.url + path,
            params=data,
            headers=headers
        )
        r.raise_for_status()
        return r.json()

    def post(self, path, data, extra_headers = {}):
        headers = {
            'x-helplightning-api-key': self.api_key,
            'Authorization': self.token
        }
        return self._post_minimal(
            path,
            data,
            extra_headers=headers
        )

    def post_no_token(self, path, data, extra_headers = {}):
        return self._post_minimal(
            path,
            data,
            extra_headers={
                'x-helplightning-api-key': self.api_key
            }
        )

    def _post_minimal(self, path, data, extra_headers = {}):
        headers = {
            'Content-Type': 'application/json'
        }
        headers.update(extra_headers)
        r = requests.post(
            self.url + path,
            data=json.dumps(data),
            headers=headers
        )
        r.raise_for_status()
        return r.json()

    def put(self, path, data, extra_headers = {}):
        headers = {
            'x-helplightning-api-key': self.api_key,
            'Authorization': self.token,
            'Content-Type': 'application/json'
        }
        headers.update(extra_headers)
        r = requests.put(
            self.url + path,
            data=json.dumps(data),
            headers=headers
        )
        r.raise_for_status()
        return r.json()

    def delete(self, path, extra_headers = {}):
        headers = {
            'x-helplightning-api-key': self.api_key,
            'Authorization': self.token,
            'Content-Type': 'application/json'
        }
        headers.update(extra_headers)
        r = requests.delete(
            self.url + path,
            headers=headers
        )
        r.raise_for_status()
        return r.json()

    ###########################
    # END HTTP methods
    ###########################


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        req_url = urllib.parse.urlsplit(self.path)
        if req_url.path == '/callback':
            params = urllib.parse.parse_qs(req_url.query)
            if params['state'][0] !=  self.server.state:
                raise ValueError(f"Generated OAuth 2 state doesn't match returned state!")
            self.send_success()
            self.server.token = params['primary_token'][0]
        else:
            self.send_error(404)
            raise ValueError(f'Request path {req_url.path} not recognized')

    def send_success(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        msg = '''
<!DOCTYPE html>
<html>
  <body>
    <h1>You may close this window.</h1>
  </body>
</html>
'''
        self.wfile.write(bytes(msg, "utf-8"))

    def log_request(self, code='-', size='-'):
        # Don't log incoming requests to stdout
        pass

class CallbackServer(http.server.HTTPServer):
    def __init__(self, host, port, state, handler):
        super().__init__((host, port), handler)
        self.state = state
