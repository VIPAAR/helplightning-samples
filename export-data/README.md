# export_data.py
This script will export user and call data to csv files which will be
packaged up into an encrypted 7zip file in the current directory.

The script will only pull the users and groups that have changed or calls
that have occured since the last run of the script, which is logged to a file
called last_run.json in the current directory. If last_run.json doesn't
exist, the script will pull all data for all time.

## Requirements
- 7zip command line tool
- Python 3 and Pip

## Installing Dependcies
```
pip install -r requirements.txt
```

## Usage
```
python3 export_data.py
```
