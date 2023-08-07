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

Make sure you have run the following in the parent directory:
```
pip install -r requirements.txt
```

## Configuring the Script

Please make sure you have configured the `siteconfig.py` in the parent directory.


## Usage

The script can be run in one of two modes: incremental or full.

The incremental mode will fetch all data on the first run, and then on subsequent runs, fetch only those users and groups which have been updated and calls that have been made since the time of the previous run. This is tracked in a local file named last_run.json. If this file doesn't exist, the script will not do an incremental run, and instead pull all data.

To run the script in this mode, execute the script with no command line options added:
```
python3 export_data_groups.py group_id zip_password
```

Running the script in full mode will ignore the last_run.json file and always pull the entire set of data on every run. To run the script in this mode, use the `--fetch-all` option:
```
python3 export_data_groups.py --fetch-all group_id zip_password
```
