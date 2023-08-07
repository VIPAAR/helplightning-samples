# Generate Report

This script will generate a server side report of calls, poll the
server for when the report is complete, then download the report.

You can choose whether to generate a JSON formatted report (the
default) or a CSV formatted report.

## Requirements

- Python 3 and Pip

## Install Dependencies


Make sure you have run the following in the parent directory:
```
pip install -r requirements.txt
```

## Configuring the Script

Please make sure you have configured the `siteconfig.py` in the parent directory.

## Usage

The script by default generates a json file. Pass in the `--csv`
option to generate a CSV file.

```
python3 generate_report.py output.json
```

Or as a CSV:
```
python generate_report.py --csv output.csv
```
