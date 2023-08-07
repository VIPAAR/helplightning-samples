# Impersonate User

This script will allow a Workspace Admin to obtain a token as one of
the users in their workspace. Using that token, they can then login or
impersonate that user using the API.

## Requirements

- Python 3 and Pip

## Install Dependencies

```
pip install -r requirements.txt
```

## Configuring the Script

You'll need an API key and a partner key to grant the script access to your site. Follow the steps in [Creating an API Key](https://apidocs.helplightning.net/background/api-keys/) and [Creating a Partner Key](https://apidocs.helplightning.net/background/partner-keys/) if you haven't already done so.

Open the script in a text editor and fill in the variables at the top of the file.
```
HL_API_KEY = ''
HL_API_URL = 'https://api.helplightning.net/api'
ENTERPRISE_ID = ''
```

## Usage

```
python3 impersonate_user.py /PATH/TO/PARTNER_KEY email_of_user_to_impersonate
```

