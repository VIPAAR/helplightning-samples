# helplightning-samples
Example scripts of using the HelpLightning API and SDK.

## Configuration

You will first need to install the necessary python dependencies:

```
pip install -r requirements.txt
```

Then, please edit the `siteconfig.py` and replace the variables with
your `API_KEY`, `PARTNER_KEY`, and `SITE_ID`.

## Available Samples
- [Export Data](export-data) - This script uses the Help Lightning RESTful API to create an encrypted 7-Zip archive of users, groups, and calls in the specified site. It can be used to create a one-time full export of all data, or if executed on a schedule, create incremental backups of data.

- [Export Data Groups](export-data-groups) - This script uses the Help Lightning RESTful API to create an encrypted 7-Zip archive of users and calls in a specific group in the specified site. It can be used to create a one-time full export of all data, or if executed on a schedule, create incremental backups of data.

- [Generate Report](generate-report) - This script uses the Help Lightning RESTful API to generate a server side report (either JSON or CSV), wait for the report to complete, then download it as a zip file.

- [Download Attachments](download-attachments) - This is a script that runs a small web server and listens for an attachment_created webhook, and automatically downloads the attachment (recording/screen captures/...)
