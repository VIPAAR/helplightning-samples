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

try:
    sys.path.append('.')
    import libhelplightning
    import siteconfig
except ImportError:
    sys.path.append('..')
    import libhelplightning
    import siteconfig

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
        'sub': f'Partner:{siteconfig.SITE_ID}',
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
        token = generate_token(partner_key)
        e_client = libhelplightning.GaldrClient(
            logger,
            siteconfig.HELPLIGHTNING_ENDPOINT,
            siteconfig.API_KEY,
            token = token
        )
        r = e_client.get(f'/v1r1/enterprise/reports/calls/{report_uuid}')
        if r['status'] == 'complete':
            print('')
            return r['url']
        elif r['status'] == 'failed':
            raise Exception('Report failed to generate!')
        else:
            time.sleep(5)

def go(output, csv):
    logger = get_logger(level = logging.INFO)
    token = generate_token(siteconfig.PARTNER_KEY)
    e_client = libhelplightning.GaldrClient(
        logger,
        siteconfig.HELPLIGHTNING_ENDPOINT,
        siteconfig.API_KEY,
        token = token
    )

    # start the generation of our report
    report_uuid = generate_report(e_client, csv)

    # now poll every 15 seconds to check if the report is done
    url = poll(siteconfig.PARTNER_KEY, report_uuid)

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
        'output',
        help='The name of the output file to generate (will be a zip file)'
    )
    parser.add_argument(
        '--csv',
        action='store_true',
        help='Generate a CSV report (Default is JSON)'
    )

    args = parser.parse_args()

    go(args.output, args.csv)
