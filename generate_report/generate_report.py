#!/usr/bin/env python3

import argparse
import datetime
import getpass
import json
import jwt
import logging
import requests
import sys
import time
import urllib

# These must be filled in
HL_API_KEY = ''
HL_API_URL = 'https://api.helplightning.net/api'
ENTERPRISE_ID = ''


def get_logger(level=logging.DEBUG):
    """
    Sets up logging to be shared across
    all classes/functions.
    """
    root = logging.getLogger()
    root.setLevel(level)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    root.addHandler(ch)
    return root


class HLClient:
    def __init__(self, logger, url, api_key, token):
        self.lg = logger
        self.url = url
        self.api_key = api_key
        self.token = token

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
        page = 1
        resp = self.get(
            path + '?page={}&page_size={}'.format(page, page_size),
            data,
            extra_headers
        )
        entries = resp.get('entries')
        callback(entries)
        while resp.get('total_entries', 0) > page * page_size:
            try:
                resp = self.get(
                    path + '?page={}&page_size={}'.format(page+1, page_size),
                    data,
                    extra_headers
                )
                entries = resp.get('entries')
                callback(entries)
                page += 1
            except requests.exceptions.RequestException as e:
                # retry
                print('Error making request', e)
                print('Retrying...')
                pass

        return True

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

    def post(self, path, data, extra_headers={}):
        headers = {
            'x-helplightning-api-key': self.api_key,
            'Authorization': self.token
        }
        return self._post_minimal(
            path,
            data,
            extra_headers=headers
        )

    def post_no_token(self, path, data, extra_headers={}):
        return self._post_minimal(
            path,
            data,
            extra_headers={
                'x-helplightning-api-key': self.api_key
            }
        )

    def _post_minimal(self, path, data, extra_headers={}):
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

    ###########################
    # END HTTP methods
    ###########################


def generate_token(partner_key):
    # create a date that expires in 1 minutes
    # It is best to use tokens with short-expirations and generate
    #  them before each call. These cannot be revoked, so if you
    #  generate a token with a long expiration and it is leaked, the only
    #  way to invalid it is to rotate your partner key, which affects
    #  every application using that key!
    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=60)

    # load our private key, which is in pkcs8 format
    with open(partner_key) as f:
        secret = f.read()

    # generate a new JWT token that will be valid for one hour and sign it with our secret
    payload = {
        'iss': 'Ghazal',
        'sub': f'Partner:{ENTERPRISE_ID}',
        'aud': 'Ghazal',
        'exp': exp
    }

    token = jwt.encode(payload, key=secret, algorithm='RS256')

    return token

def generate_report(client, csv):
    report_url = '/v1r1/enterprise/reports/calls'
    if not csv:
        report_url = report_url + '.json'

    r = client.post(report_url, {})
    return r['uuid']

def poll(partner_key, report_uuid):
    logger = get_logger(level = logging.INFO)
    print('Waiting on report to complete: ', end = '', flush = True)
    while True:
        print('.', end = '', flush = True)
        e_client = HLClient(logger,
                            HL_API_URL,
                            HL_API_KEY,
                            generate_token(partner_key))
        r = e_client.get(f'/v1r1/enterprise/reports/calls/{report_uuid}')
        if r['status'] == 'complete':
            print('')
            return r['url']
        elif r['status'] == 'failed':
            raise Exception('Report failed to generate!')
        else:
            time.sleep(5)

def go(partner_key, output, csv):
    logger = get_logger(level = logging.INFO)
    e_client = HLClient(logger,
                        HL_API_URL,
                        HL_API_KEY,
                        generate_token(partner_key))

    # start the generation of our report
    report_uuid = generate_report(e_client, csv)

    # now poll every 15 seconds to check if the report is done
    url = poll(partner_key, report_uuid)

    print('Downloading')
    u = urllib.parse.urlparse(url)
    path = f'{u.scheme}://{u.hostname}{u.path}'
    params = urllib.parse.parse_qs(u.query)

    r = requests.get(path, params = params)
    with open(output, 'wb') as f:
        f.write(r.content)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'partner_key',
        help='The location on disk of a partner key to use for generating tokens'
    )
    parser.add_argument(
        'output',
        help='The name of the output file to generate (will be a zip file)'
    )
    parser.add_argument(
        '--csv',
        action='store_true',
        help='Generate a CSV report (Default is JSON)'
    )

    args = parser.parse_args()

    go(args.partner_key, args.output, args.csv)
