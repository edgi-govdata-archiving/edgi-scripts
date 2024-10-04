# EDGI Scripts

[![Code of Conduct](https://img.shields.io/badge/%E2%9D%A4-code%20of%20conduct-blue.svg?style=flat)](https://github.com/edgi-govdata-archiving/overview/blob/main/CONDUCT.md) [![Scheduled Zoom → YT Uploads][zoom-upload-action-badge]][zoom-upload-action-runs]

Helper scripts for EDGI's digital infrastructure.

We use this as a catch-all for simple scripts that help with repeating tasks. Many of them run automatically in the cloud.

## Table of Contents

- [Technologies Used](#technologies-used)
- [About These Automated Scripts](#about-these-automated-scripts)
- [Script Catalog](#script-catalog)

## Technologies Used

- **Python >=3.8.** A programming language common in scripting.
- [**Click.**][click] A Python library for writing simple command-line
  tools.
- [**GitHub Actions.**][github-actions] A script-running service that runs scheduled
  tasks for us in the cloud.

## About these Automated Scripts

Some of these scripts are run automatically at regular intervals,
using GitHub's "actions workflow" feature. The schedule is set in the
[`.github/workflows/zoom-upload.yml`](.github/workflows/zoom-upload.yml) file within this repo.

## Script Catalog

### Backup to Internet Archive: `archive.sh`

This script is used to run periodically and ensure that recent copies of
the EDGI website are backed up to the Internet Archive.

This script is not run automatically.

**Usage**

```
bash scripts/archive.sh envirodatagov.org
```

### Convert Zoom timestamps for YouTube: `convert_transcript_timestamps.py`

This script is used from the local workstation to convert the Zoom chat
text transcript into a form that's friendly to post into YouTube video
descriptions or comments. When the Zoom timestamps are shifted to
account for when the recording started, then the timecodes will link
directly to the spot in the video where the comment was made.

This script is not run automatically.

- [Sample chat transcript](https://gist.github.com/patcon/68820d1eb90c0bd707c773ce57312d92)

See commands

**Usage**

```
python scripts/convert_transcript_timestamps.py --help
python scripts/convert_transcript_timestamps.py transcript.txt > transposed-transcript.txt
```

### Zoom-to-YouTube Uploader: `upload_zoom_recordings.py` and `auth.py`

This script cycles through each Zoom cloud recording longer than 60
seconds in duration and:

* uploads video to youtube as unlisted video
* sets video title to be `<Zoom title> - Mmm DD, YYYY` of recorded date
* sets video license to "Creative Commons - Attribution"
* sets video category to "Science & Technology"
* adds video to a default unlisted playlist, "Uploads from Zoom"
* adds video to a call-specific playlist based on meeting title and top (if
    there is a relevant playlist). You can see the playlists in
    [`upload_zoom_recordings.py`](./scripts/upload_zoom_recordings.py).
* **deletes** original video file from Zoom (**not** audio or chat log)

This script is run every hour.

Note: the script isn't smart enough to detect duplicate videos being
uploaded more than once, but YouTube will recognize and disable them
after upload

#### Usage via GitHub Actions

**For forcing a cloud run on-demand:** Visit [the actions page][zoom-upload-action-runs] and click the “run workflow” button near the top-right. In the popup, select your options and click “run workflow.” (You will
need to have the right permissions set to click the button.)

#### Local Usage

##### Setup

Quick reference for Ubuntu (may vary).

```sh
apt-get install python python-pip
python -m venv .venv-edgi-scripts
# To activate the virtualenv:
source .venv-edgi-scripts/bin/activate
```

Get Python 3.8. This packages makes use of modern Python features and requires Python 3.8+. If you don't have Python 3.8, we recommend using [conda][conda] to install it. (You don't need admin privileges to install or use it, and it won't interfere with any other installations of Python already on your system.)

##### Usage

```sh
pip install -r requirements.txt

# Copy `.env.sample` to `.env` for you own local use, then manually fill in the
# values.
cp .env.sample .env
vim .env

# Load the secrets from `.env` into your current environment.
source .env

# To use the existing EDGI youtube-uploader app, decrypt its secrets:
openssl aes-256-cbc -k "$EDGI_ZOOM_API_SECRET" -in client_secret.json.enc -out client_secret.json -d -md sha256
# ALTERNATIVELY, to use a new set of Google Cloud app credentials, copy your new
# `client_secret.json` to the repo root directory. You can download it from the
# Google API Console. See:
# See: https://github.com/tokland/youtube-upload#setup

# Authorize the script to use EDGI's YouTube account.
# This needs to be done from a system with a windowed browser (i.e. not a
# server). It will generate a file named `.youtube-upload-credentials.json` in
# the repo root dir. If running the script on a server is required, you will
# need to transfer this file from your workstation onto the server.
python scripts/auth.py

# Download from Zoom and upload to YouTube
python scripts/upload_zoom_recordings.py
```

#### Authorization

This script needs authorized access to EDGI’s Zoom account and YouTube account
in order to do its work.

##### Zoom

To access the Zoom API, you have to create a Zoom *app*. Ours is not published,
so it can only be used in EDGI’s Zoom account. For the scripts to access Zoom
through the app, they require 3 values that are stored in environment variables:

1. `EDGI_ZOOM_ACCOUNT_ID`
2. `EDGI_ZOOM_CLIENT_ID`
3. `EDGI_ZOOM_CLIENT_SECRET`

You can find the appropriate value’s on the app’s “App Credentials” page. You
can get to that by going to the [App Marketplace](https://marketplace.zoom.us),
clicking on “manage” in the top right, and clicking on the app in the list of
“created apps.”

##### YouTube

YouTube authorization is slightly more complicated. We have a Google Cloud *app*
that represents our script. Our YouTube account must then authorize that app to
act on its behalf to upload videos. That authorization periodically expires and
needs to be manually recreated.

The basic credentials for the app are stored (encrypted) in
`client_secret.json.enc`. The *authorization* for the app to work in YouTube is
stored (encrypted) in `.youtube-upload-credentials.json.enc`. When the
`upload_zoom_recordings.py` script runs, it simply uses the authorization file.
If the authorization is expired, you can generate a new one from the app’s
credentials (in `client_secret.json.enc`) using the `auth.py` script:

1. Decrypt the `client_secret.json.enc` file:

    ```sh
    # Ensure you have `EDGI_ZOOM_API_SECRET` set to the decryption key.
    openssl aes-256-cbc -d -k "$EDGI_ZOOM_API_SECRET" -in client_secret.json.enc -out client_secret.json -md sha256
    ```

2. Run the authorization script. It will open a browser window to a YouTube login page, where you should log into EDGI’s YouTube account. Then it will ask you to authorize the app. Afterward, you can close the window.

    ```sh
    python scripts/auth.py
    ```

    The script should have created a file named `.youtube-upload-credentials.json`.

3. Encrypt the authorization:

    ```sh
    openssl aes-256-cbc -e -k "$EDGI_ZOOM_API_SECRET" -in .youtube-upload-credentials.json -out .youtube-upload-credentials.json.enc
    ```

4. Commit the new authorization to git for later use!

    ```sh
    git add .youtube-upload-credentials.json.enc
    git commit
    git push
    ```

# Contributing Guidelines

We love improvements to our tools! EDGI has general [guidelines for
contributing](https://github.com/edgi-govdata-archiving/overview/blob/main/CONTRIBUTING.md)
to all of our organizational repos.

For repo-specific details, see our [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License & Copyright

Copyright (C) 2017 Environmental Data and Governance Initiative (EDGI)
This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, version 3.0.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See the [`LICENSE`](/LICENSE) file for details.

<!-- Links -->
[click]: http://click.pocoo.org/5/
[conda]: https://conda.io/miniconda.html
[github-actions]: https://github.com/edgi-govdata-archiving/edgi-scripts/actions
[zoom-upload-action-runs]: https://github.com/edgi-govdata-archiving/edgi-scripts/actions/workflows/zoom-upload.yml
[zoom-upload-action-badge]: https://github.com/edgi-govdata-archiving/edgi-scripts/actions/workflows/zoom-upload.yml/badge.svg?event=schedule
