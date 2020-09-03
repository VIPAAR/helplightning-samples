# Export Data Groups
This script will export user and call data to csv files which will be
packaged up into an encrypted 7-Zip file in the current directory.

This is similar to the Export Data, except this will only export data for users in a specific group.

The script will only pull the users and groups that have changed or calls
that have occured since the last run of the script, which is logged to a file
called last_run.json in the current directory. If last_run.json doesn't
exist, the script will pull all data for all time.

## Requirements
- 7-Zip command line tool
- Python 3 and Pip

## Installing Dependencies
```
pip install -r requirements.txt
```

## Configuring the Script
You'll need an API key and a partner key to grant the script access to your site. Follow the steps in [Creating an API Key](#creating-an-api-key) and [Creating a Partner Key](#creating-a-partner-key) if you haven't already done so.

Once you have an API key, follow the steps in [Finding Your Enterprise ID](#finding-your-enterprise-id)

Open the script in a text editor and fill in the variables at the top of the file.
```
HL_API_KEY = ''
HL_API_URL = 'https://api.helplightning.net/api'
ENTERPRISE_ID = ''
GROUP_ID = ''
ZIP_PASSWORD = r''
```

### Creating an API Key

> Note: You'll need to be an administrator in your site to make these changes.

1. Navigate to the Enterprise Settings at https://helplightning.net/admin/enterprise.
2. Click on the **Developer** tab.
3. Scroll to the **API Keys** section and click **Add API Key**.

### Creating a Partner Key
The partner key consists of a public/private key pair. The script will need access to the private key in order to generate JWT tokens which grant access to resources in your site. Make sure this key is saved in a secure way.

You can only have one active partner key at a time. If you or someone in your site has already created a partner key, then creating a new one will invalidate the old key. This will break requests that use the old key to generate tokens, so only replace existing keys if you are sure you no longer need it! If you have an existing key, you will see the corresponding public key in the Developer section of the Help Lightning web app. The private keys are not stored by Help Lightning.

> Note: You'll need to be an administrator in your site to make these changes.

1. Navigate to the Enterprise Settings at https://helplightning.net/admin/enterprise
2. Click on the **Developer** tab.
3. Scroll to the **Partner Key** section.
4. If you see a public key listed, then you already have a partner key. Proceed with caution, as creating a new partner key will invalidate the old key.
5. Click **Create Partner Key**.
6. Save the private key securely. This is not stored by Help Lightning and can not be recovered after leaving this page.

### Finding Your Enterprise ID

1. Create an API key by following the steps in [Creating an API Key](#creating-an-api-key).

2. Create a temporary file that contains Help Lightning login credentials for a user in your site. The file should be in the following format. 

   ```
   {
       "email": "youremail@example.com",
       "password": "yourPassword"
   }
   ```

3. Use the curl command line tool to obtain a JWT user token, filling in the values for your API key and credentials file.

   ```
   curl 'https://api.helplightning.net/api/v1/auth' -H 'x-helplightning-api-key: yourApiKey' -H 'Content-Type: application/json' -d @/path/to/yourCredentialsFile
   ```

4. Use the token returned in the previous step to get information about your user account, which includes your enterprise id.

   ```
   curl 'https://api.dev.helplightning.net/api/v1r1/user' -H 'x-helplightning-api-key: yourApiKey' -H 'authorization: yourJwtToken' -H 'Accept: application/json'
   ```

## Usage

The script can be run in one of two modes: incremental or full.

The incremental mode will fetch all data on the first run, and then on subsequent runs, fetch only those users and groups which have been updated and calls that have been made since the time of the previous run. This is tracked in a local file named last_run.json. If this file doesn't exist, the script will not do an incremental run, and instead pull all data.

To run the script in this mode, execute the script with no command line options added:
```
python3 export_data_groups.py partner_key_filename
```

Running the script in full mode will ignore the last_run.json file and always pull the entire set of data on every run. To run the script in this mode, use the `--fetch-all` option:
```
python3 export_data_groups.py --fetch-all partner_key_filename
```
