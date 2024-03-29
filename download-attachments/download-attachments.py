#!/usr/bin/env python3
#
# This is meant to respond to help lightning webhooks
#  and automatically download attachments.

import os
import http.server
import json
import threading
import queue
import jwt
import datetime
import logging
import requests
import sys
import argparse
import hashlib
import hmac


try:
    sys.path.append('.')
    import libhelplightning
    import siteconfig
except ImportError:
    sys.path.append('..')
    import libhelplightning
    import siteconfig

PORT = 8080

class DownloadPool:
    def __init__(self, size = 2):
        self.__queue = queue.Queue()
        self.__stop_queue = queue.Queue()
        self.__size = size
        
        self.__pool = [Runner(self.__queue, self.__stop_queue) for x in range(self.__size)]
        for i in self.__pool:
            i.start()

    def queue(self, attachment):
        self.__queue.put(attachment)

    def stop(self):
        self.__stop_queue.put(True)

        for p in self.__pool:
            p.join()
        
class Runner(threading.Thread):
    def __init__(self, job_queue, stop_queue):
        super().__init__()
        
        self.__job_queue = job_queue
        self.__stop_queue = stop_queue

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

        
    def run(self):
        while self.__stop_queue.empty():
            try:
                job = self.__job_queue.get(timeout = .1)
                # do something with job
                call_id = job['data']['call_id']
                attachment_id = job['data']['attachment']['id']

                logger = self.get_logger(level=logging.INFO)
                token = self.generate_token(siteconfig.PARTNER_KEY)
                e_client = libhelplightning.GaldrClient(
                    logger,
                    siteconfig.HELPLIGHTNING_ENDPOINT,
                    siteconfig.API_KEY,
                    token = token
                )
                resp = e_client.get(f'/v1r1/enterprise/calls/{call_id}/attachments')

                #print(resp)

                # filter for the attachment we want
                res = filter(lambda x: x['id'] == attachment_id, resp)
                a = list(res)[0]

                url = a['signed_url']
                name = a['name']

                path = os.path.join('.', 'attachments', str(call_id), str(attachment_id))
                try: os.makedirs(path)
                except OSError: pass

                print(f'Downloading {name}')
                with open(os.path.join(path, name), 'wb') as f:
                    r = requests.get(url, stream = True)
                    for l in r.iter_content(512):
                        f.write(l)
                print(f'Completed download of {name}')

            except queue.Empty:
                pass
            except Exception as e:
                print('Runner raised an exception:', e)
                pass

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

class MyServer(http.server.HTTPServer):
    def __init__(self, host, port, pool, verify_signature, handler):
        super().__init__((host, port), handler)
        self.pool = pool
        self.verify_signature = verify_signature != None
        self.signature = verify_signature
            
class MyHandler(http.server.BaseHTTPRequestHandler):
    '''
    A simple webserver that responds to either:
    GET /call
    GET /session

    However, it only currently takes action on
    GET /call
    when the category is an attachment_created
    '''
    def do_GET(self):
        self.do_404()

    def do_POST(self):
        path = self.path
        content_length = int(self.headers['Content-Length'])
        data = self.rfile.read(content_length)

        if self.server.verify_signature:
            self.verify_signature(self.headers['x-helplightning-signature'], data)
        
        if path == '/call':
            self.do_calls(data)
        elif path == '/session':
            self.do_sessions(data)
        else:
            self.do_404()

    def do_calls(self, data):
        att = json.loads(data)

        # TODO, validate the HMAC signature!!
        
        if att['category'] == 'attachment_created':
            # queue up a download
            self.server.pool.queue(att)
        self.do_response()

    def do_sessions(self, data):
        self.do_response()

    def do_response(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(bytes("ok\n", "utf-8"))

    def do_404(self):
        self.send_response(404)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        msg = '''
<!DOCTYPE html>
<html>
  <body>
    <h1>Not Found!</h1>
  </body>
</html>
        '''
        
        self.wfile.write(bytes(msg, "utf-8"))

    def verify_signature(self, signature_header, body):
        # calculate the signature to validate its
        #  authenticity
        hash_object = hmac.new(self.server.signature.encode('utf-8'), msg=body, digestmod=hashlib.sha256)
        expected_signature = "sha256=" + hash_object.hexdigest()

        if not hmac.compare_digest(expected_signature, signature_header):
            raise http.client.HTTPException(status_code=403, detail="Request signatures didn't match!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--verify-signature',
        help='Secret used to verify webhook signature'
    )
    args = parser.parse_args()
    
    # create a pool
    pool = DownloadPool()
    
    s = MyServer("localhost", PORT, pool, args.verify_signature, MyHandler)
    try:
        s.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        s.server_close()
        pool.stop()

