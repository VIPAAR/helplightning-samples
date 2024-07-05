#!/usr/bin/env python3
"""
License: MIT License
Copyright (c) 2023 Miel Donkers

Very simple HTTP server in python for logging requests
Usage::
    ./server.py [<port>]
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import sys
import datetime
import json
import jwt
import os
import time
from os import walk

sys.path.append('.')
import libhelplightning
import siteconfig

current_dir = "/" + sys.path[0] + "/"

class S(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def get_logger(self, level=logging.DEBUG):
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

    def generate_token(self, partner_key):
        # create a date that expires in 1 hour
        exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=3600)

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

    def save_data(self, call_id, uuid, attachement_id):
        writepath = current_dir + call_id
        mode = 'a' if os.path.exists(writepath) else 'w'
        with open(writepath, mode) as f:
            f.write(uuid + ',' + str(attachement_id) + '\n')

    def save_recording_info(self, uuid, tag):
        rec = self.get_recording_info()

        if uuid not in rec:
            writepath = current_dir + 'rec_' + str(datetime.date.today())
            now = datetime.datetime.now()
            dt_string = now.strftime("%d/%m/%Y-%H:%M:%S")
            mode = 'a' if os.path.exists(writepath) else 'w'
            with open(writepath, mode) as f:
                f.write(tag + ',' + uuid + ',' + dt_string +'\n')

    def get_recording_info(self):
        path = current_dir + 'rec_' + str(datetime.date.today())
        dictionary = {}
        if os.path.exists(path):
            with open(path, 'r') as file:
                lines = file.readlines()
                for line in lines:
                    line = line.strip()
                    data = line.split(",")
                    dictionary[data[1]] = [data[0], data[2]]

        logging.info("\n %s", dictionary)
        return dictionary

    def get_cached_files(self, prefix):
        filenames = next(walk(current_dir), (None, None, []))[2]
        files = filter(lambda x: x.startswith(prefix), filenames)
        return list(files)

    def get_attachments_from_uuid(self, uuids):
        calls = self.get_cached_files('call_')
        dictionary = {}
        for f in calls:
            with open(current_dir + f, 'r') as file:
                lines = file.readlines()
                for line in lines:
                    line = line.strip()
                    data = line.split(",")
                    if data[0] in uuids:
                        dictionary[data[1]] = f # {attachment_id: call_id}


        logging.info("\n %s", dictionary)
        return dictionary

    def get_call_attachments(self, call_attachment_dict):
        logger = self.get_logger(level=logging.INFO)
        token = self.generate_token(siteconfig.PARTNER_KEY)
        e_client = libhelplightning.GaldrClient(
                logger,
                siteconfig.HELPLIGHTNING_ENDPOINT,
                siteconfig.API_KEY,
                token = token
            )
        attachments = {}

        for attachment_id, call_id in call_attachment_dict.items():
            time.sleep(0.100)
            resp = e_client.get(f'/api/v1r1/enterprise/calls/{call_id}/attachments/{attachment_id}')
            attachments[resp.get("uuid")] = resp.get("signed_url")

        return attachments

    def do_GET(self):
        self.path = current_dir + 'index.html'
        logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        file_to_open = open(self.path[1:]).read()
        self._set_response()
        self.wfile.write(bytes(file_to_open, 'utf-8'))

    def do_POST(self):
        response = "{}"
        content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
        post_data = self.rfile.read(content_length) # <--- Gets the data itself
        logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
                str(self.path), str(self.headers), post_data.decode('utf-8'))

        call_data = json.loads(post_data.decode('utf-8'))

        type = call_data.get("type")
        category = call_data.get("category")

        if type == "call" and category == "attachment_created":
            uuid = call_data.get("data").get("attachment").get("uuid")
            attachement_id = call_data.get("data").get("attachment").get("id")
            call_id = call_data.get("data").get("call_id")

            logging.info("\nAttachment: id - %s \n call_id: %s \n uuid: %s \n", attachement_id, call_id, uuid)
            self.save_data(call_id, uuid, attachement_id)


        if type == "load":
            local_rec = self.get_recording_info()
            uuids = []
            for x in local_rec.keys():
                uuids.append(x)

            call_attachment_dict = self.get_attachments_from_uuid(uuids)
            attachments = self.get_call_attachments(call_attachment_dict)
            data = []
            for x in local_rec.keys():
                url = attachments.get(x, "")
                name = local_rec[x][0]
                time = local_rec[x][1]
                data.append({"uuid": x, "url": url, "name": name, "time": time})

            response = json.dumps(data)

        if type == "start_recording":
            uuid = call_data.get("uuid")
            tag = call_data.get("tag")
            self.save_recording_info(uuid, tag)

        if type == "reset":
            files = self.get_cached_files('call_') + self.get_cached_files('rec_')
            for f in files:
                os.remove(current_dir + f)
            response = []

        self._set_response()
        self.send_header('Content-Type', 'application/json')
        self.wfile.write(response.encode('utf-8'))

def run(server_class=HTTPServer, handler_class=S, port=8899):
    logging.basicConfig(level=logging.INFO)
    #logging.info(sys.path)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd...\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping httpd...\n')


if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
