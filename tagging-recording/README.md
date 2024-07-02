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

This script will start up an HTTP server on port 8899.
It is recommanded to set up another public web service and forward the web hook request to server.

## Usage

The script will start up a web server on port 8899 and will listen for
incoming webhooks of type `call` with a category of `attachment_created`.

Each time it gets a new `attachment_created` event, the script will
save the attachment id and uuid to the file named with call id.

```
> cat call_34c78f14-55a7-4d16-86c1-a6fe7837cf26
5895ec01-c02c-42db-983a-9fdae98d0ace,31675
a7c1de42-9900-41e6-9ef4-cdabf01d45e3,31674
95d4f7a9-d5b8-46df-a3fc-504c51845910,31676
4aec6d2a-263d-4227-9248-6d3d10592668,31677
f4a753f2-ee63-4ec7-adaf-5044c88a7dcd,31678

```

To run this script:

```
python3 server.py
```
