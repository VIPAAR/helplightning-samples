# Download Attachments

This script will start up a local HTTP server and listen for webhooks
from Help Lightning. When it gets an `attachment_created` webhook, it
will download the attachment to the local disk.

## Requirements

- Python 3 and Pip

## Install Dependencies

Make sure you have run the following in the parent directory:
```
pip install -r requirements.txt
```

## Configuring the Script

Please make sure you have configured the `siteconfig.py` in the parent directory.

## Set up a Reverse Proxy

This script will start up an HTTP server on port 8080. However, for
this script to receive webhooks from Help Lightning, it will need to
be publicly available on the Internet and behind an HTTPS server!

**Help Lightning will _NOT_ accept an unsecured HTTP server for a
webhook!**

A quick way to open up this server would be to use a service like
[ngrok](ngrok.com/):

```
nrok http 8080
```

## Configure the Webhooks

In Help Lightning, you will then need to configure a `call` webhook that
points back to your base domain with the `/calls` path. For example:

https://e058-73-78-85-105.ngrok-free.app/calls

You can read more about configuring webhooks on [Help Lightning's
Webhook Documentation](https://apidocs.helplightning.net/sdks/server/webhooks/).

## Usage

The script will start up a web server on port 8080 and will listen for
incoming webhooks of type `call` with a category of `attachment_created`.

Each time it gets a new `attachment_created` event, the script will
query for information about the attachment and download it
automatically to the following directory structure:

```
attachments/${call_id}/${attachment_id}/${attachment_name}
```

To run this script:

```
python3 download-attachments.py
```

If you created a secret when setting up your webhooks, you can also
verify the incoming webhooks:

```
python3 download-attachments.py --verify-signature your-secret
```
