#!/usr/bin/env python3

import argparse
import csv
import datetime
import getpass
import hashlib
import json
import jwt
import logging
import os
import requests
import sys
import tempfile

# These must be filled in
HL_API_KEY = ''
HL_API_URL = 'https://api.helplightning.net/api'
GROUP_ID = ''
ENTERPRISE_ID = ''
ZIP_PASSWORD = r''


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
    # create a date that expires in 1 hour
    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=3600)

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


def write_users(e_client, group_id, start_date, base):
    def query_params():
        if not start_date:
            return {}
        else:
            # updates since the last run
            s = start_date.isoformat().replace('+00:00', 'Z')
            return {'filter': f'updated_at>{s}'}

    params = query_params()

    filter_params = [
        'id',
        'active',
        'available',
        'confirmation_sent_at',
        'confirmed_at',
        'created_at',
        'email',
        'email_confirmed',
        'enterprise_id',
        'first_call_at',
        'invitation_sent_at',
        'is_confirmed',
        'is_first_login',
        'last_used_at',
        'license',
        'location',
        'manage',
        'name',
        'provider',
        'provider_uid',
        'role_id',
        'role_name',
        'status',
        'status_message',
        'title',
        'unavailable_expires_at',
        'updated_at',
        'username'
    ]

    with open(os.path.join(base, 'users.csv'), 'w', newline='') as users_csv:
        # Set up csv writer
        fieldnames = [p for p in filter_params]
        writer = csv.DictWriter(users_csv, fieldnames)
        writer.writeheader()

        def cb(entries):
            results = []
            for e in entries:
                row = {}
                for p in filter_params:
                    row[p] = e[p]

                writer.writerow(row)
                
                results.append(e['id'])

            return results

        user_ids = e_client.get_all_cb(cb, f'/v1/enterprise/pods/{group_id}/users', params)

        return user_ids


def write_pods(e_client, user_ids, start_date, base):
    def query_params():
        if not start_date:
            return {}
        else:
            # updates since the last run
            s = start_date.isoformat().replace('+00:00', 'Z')
            return {'filter': f'updated_at>{s}'}

    params = query_params()
    results = e_client.get_all('/v1r1/enterprise/pods', params)

    filter_params = [
        "id",
        "admin_count",
        "default",
        "description",
        "email",
        "expert",
        "manage",
        "name",
        "user_count"
    ]


    # Create csv files for the main table and linking tables
    pods_csv = open(os.path.join(base, 'pods.csv'), 'w', newline='')
    pods_users_csv = open(os.path.join(base, 'pods_users.csv'), 'w', newline='')
    pods_admins_csv = open(os.path.join(base, 'pods_admins.csv'), 'w', newline='')
    pods_pods_csv = open(os.path.join(base, 'pods_pods.csv'), 'w', newline='')
    pods_on_call_pods_csv = open(os.path.join(base, 'pods_on_call_pods.csv'), 'w', newline='')

    with pods_csv, pods_users_csv, pods_admins_csv, pods_pods_csv, pods_on_call_pods_csv:
        pods_writer = csv.DictWriter(pods_csv, filter_params)
        pods_writer.writeheader()

        # Get a function for creating linking tables for this enterprise.
        write_link_tables = get_pods_link_tables_writer(
            e_client,
            user_ids, 
            base,
            pods_users_csv,
            pods_admins_csv,
            pods_pods_csv,
            pods_on_call_pods_csv
        )

        for r in results:
            row = {p: r[p] for p in filter_params}
            pods_writer.writerow(row)
            write_link_tables(row['id'])


def get_pods_link_tables_writer(e_client, user_ids, base, users_file, admins_file, subpods_file, on_call_pods_file):
    # Create the csv writers
    pods_users_writer = csv.DictWriter(users_file, ['id', 'pod_id', 'user_id'])
    pods_admins_writer = csv.DictWriter(admins_file, ['id', 'pod_id', 'user_id'])
    pods_pods_writer = csv.DictWriter(subpods_file, ['id', 'pod_id', 'included_pod_id'])
    pods_on_call_pods_writer = csv.DictWriter(on_call_pods_file, ['id', 'pod_id', 'on_call_pod_id'])

    pods_users_writer.writeheader()
    pods_admins_writer.writeheader()
    pods_pods_writer.writeheader()
    pods_on_call_pods_writer.writeheader()

    def fetch_and_write(pod_id):
        results = e_client.get(f'/v1r1/enterprise/pods/{pod_id}')

        # first the pods_users
        for u in results['users']:
            u_row = {
                'id': f'{pod_id}_{u["id"]}',
                'pod_id': pod_id,
                'user_id': u['id']
            }
            if u['id'] in user_ids:
                pods_users_writer.writerow(u_row)

        # now the pods_admins
        for u in results['admins']:
            a_row = {
                'id': f'{pod_id}_{u["id"]}',
                'pod_id': pod_id,
                'user_id': u['id']
            }
            if u['id'] in user_ids:
                pods_admins_writer.writerow(a_row)

        # now the pods_pods (subpods)
        for u in results['subpods']:
            p_row = {
                'id': f'{pod_id}_{u["id"]}',
                'pod_id': pod_id,
                'included_pod_id': u['id']
            }
            pods_pods_writer.writerow(p_row)

        # now the pods_on_call_pods (on call pods)
        for u in results['on_call_pods']:
            o_row = {
                'id': f'{pod_id}_{u["id"]}',
                'pod_id': pod_id,
                'on_call_pod_id': u['id']
            }
            pods_on_call_pods_writer.writerow(o_row)

    return fetch_and_write


def write_calls(e_client, enterprise_id, group_id, start_date, base):
    def url_query_params():
        if not start_date:
            return (f'/v1/enterprise/pods/{group_id}/calls', {})
        else:
            # updates since the last run
            s = int(start_date.timestamp())
            return ('/v1/enterprise/pods/{group_id}/calls', {'filter': 'order=timeCallStarted:desc'})

    url, params = url_query_params()

    filter_params = [
        ('session', 'id', ''),
        ('callDuration', 'call_duration', 0),
        ('dialerId', 'dialer_id', '-1'),
        ('dialerName', 'dialer_name', ''),
        ('intraEnterpriseCall', 'intra_enterprise_call', True),
        ('reasonCallEnded', 'reason_call_ended', ''),
        ('receiverId', 'receiver_id', '-1'),
        ('receiverName', 'receiver_name', ''),
        ('recordingStatus', 'recording_status', ''),
        ('timestamp', 'timestamp', ''),
        ('timeCallStarted', 'time_call_started', 0),
        ('timeCallEnded', 'time_call_ended', 0)
    ]

    # Open csv files for writing user data
    calls_csv = open(os.path.join(base, 'calls.csv'), 'w', newline='')
    calls_users_csv = open(os.path.join(base, 'calls_users.csv'), 'w', newline='')

    with calls_csv, calls_users_csv:
        # Set up csv writers
        calls_fieldnames = [p[1] for p in filter_params]
        calls_writer = csv.DictWriter(calls_csv, calls_fieldnames)
        calls_writer.writeheader()

        link_table_fieldnames = ['id', 'call_id', 'user_id', 'name', 'isAnonymous', 'isExternal']
        link_table_writer = csv.DictWriter(calls_users_csv, link_table_fieldnames)
        link_table_writer.writeheader()

        def cb(entries):
            for e in entries:
                d = datetime.datetime.fromtimestamp(float(e['timestamp']))
                if start_date and e < d:
                    # stop processing, we've hit old calls we aren't interested in
                    return
                
                row = {}
                for (p0, p1, default) in filter_params:
                    if p0 in e:
                        row[p1] = e[p0]
                    else:
                        row[p1] = default

                calls_writer.writerow(row)

                # write out linking tables
                for participant in e['participants']:
                    id = f'{e["session"]}_{participant["id"]}'
                    row = {
                        'id': id,
                        'call_id': e['session'],
                        'user_id': participant['id'],
                        'name': participant['name'],
                        'isAnonymous': participant['isAnonymous'],
                        'isExternal': participant['enterpriseId'] != f'{enterprise_id}'
                    }
                    link_table_writer.writerow(row)

        e_client.get_all_cb(cb, url, params)


def go(partner_key, fetch_all):
    if ZIP_PASSWORD == '':
        print('ZIP_PASSWORD must not be empty. '
              'Edit the global variables at the top of this script.')
        sys.exit(1)

    # We'll write this timestamp out to a file at the end of the run
    utc_now = datetime.datetime.now(datetime.timezone.utc)

    # Set up the Help Lightning API client 
    logger = get_logger(level=logging.INFO)
    token = generate_token(partner_key)
    e_client = HLClient(
        logger,
        HL_API_URL,
        HL_API_KEY,
        token
    )

    if fetch_all:
        start_date = ''
    else:
        # Look for last_run.json file and only pull data that has changed since the
        # last run, otherwise pull everything
        try:
            with open('last_run.json', 'r') as f:
                last_run = json.load(f)
        except FileNotFoundError:
            # If we can't find a last_run file, the individual write_* functions
            # will know to pull everything
            logger.info("last_run.json file not found. Can't pull an incremental update, pulling all data instead")
            start_date = ''
        else:
            last_run_date = last_run['timestamp']
            start_date = datetime.datetime.fromisoformat(last_run_date)

    # Make a temporary directory to store export files before they are archived
    with tempfile.TemporaryDirectory() as base:
        user_ids = write_users(e_client, GROUP_ID, start_date, base)
        write_pods(e_client, user_ids, start_date, base)
        write_calls(e_client, ENTERPRISE_ID, GROUP_ID, start_date, base)

        # Output an encrypted 7zip file
        timestamp = utc_now.strftime('%Y%m%dT%H:%M:%SZ')
        if start_date:
            filename = f'hl_export_partial_{timestamp}'
        else:
            filename = f'hl_export_full_{timestamp}'

        os.system(f'7z a -p"{ZIP_PASSWORD}" "{filename}.7z" "{base}"')

    # Calculate a checksum for the zip and write it to a checksum file
    m = open(f'{filename}.md5', 'w')
    z = open(f'{filename}.7z', 'rb')
    with m, z:
        checksum = hashlib.md5(z.read()).hexdigest()
        m.write(checksum)

    # Update last_run.json with the datetime of this run
    with open('last_run.json', 'w') as f:
        f.write(json.dumps({'timestamp': utc_now.isoformat()}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'partner_key',
        help='The location on disk of a partner key to use for generating tokens'
    )
    parser.add_argument(
        '--fetch-all',
        action='store_true',
        help='Pull all data for all time'
    )

    args = parser.parse_args()

    go(args.partner_key, args.fetch_all)
