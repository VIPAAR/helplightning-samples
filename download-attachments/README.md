# Download Attachments

This script will start up a local HTTP server and listen for webhooks
from Help Lightning. When it gets an `attachment_created` webhook, it
will download the attachment to the local disk.

## Requirements

- Python 3 and Pip

## Install Dependencies

```
pip install -r requirements.txt
```

## Script Requirements

- Generate an [API Key](https://apidocs.helplightning.net/background/api-keys/)
- Generate a [Partner Key](https://apidocs.helplightning.net/background/partner-keys/)
- Keep Track of your Site ID (Located in the Developer Settings Tab)

## Configuring the Script

Open the script in a text editor and fill in the variables at the top of the file.

```
HL_API_KEY = ''
HL_API_URL = 'https://api.helplightning.net/api'
SITE_ID = ''
```
## Configure the Webhooks


## Set up a Reverse Proxy


## Running
