# EDGI Scripts

[![Code of Conduct](https://img.shields.io/badge/%E2%9D%A4-code%20of%20conduct-blue.svg?style=flat)](https://github.com/edgi-govdata-archiving/overview/blob/main/CONDUCT.md) [![Scheduled Zoom → GDrive Uploads][zoom-upload-action-badge]][zoom-upload-action-runs]

Helper scripts for EDGI's digital infrastructure.

We use this as a catch-all for simple scripts that help with repeating tasks. Many of them run automatically in the cloud.

## Table of Contents

- [Technologies Used](#technologies-used)
- [About These Automated Scripts](#about-these-automated-scripts)
- [Script Catalog](#script-catalog)

## Technologies Used

- [**Uv.**][uv] A Python project manager. This is the only tool you should need to install directly, it will set up all the others.
- **Python >=3.14.** A programming language common in scripting.
- [**GitHub Actions.**][github-actions] A script-running service that runs scheduled
  tasks for us in the cloud.

## About these Automated Scripts

Some of these scripts are run automatically at regular intervals,
using GitHub’s “actions workflow” feature. The schedule is set in the
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
uv run scripts/convert_transcript_timestamps.py --help
uv run scripts/convert_transcript_timestamps.py transcript.txt > transposed-transcript.txt
```

### Zoom-to-GDrive (or YouTube) Uploader: `upload_zoom_recordings.py` and `auth.py`

This script cycles through each Zoom cloud recording longer than 60
seconds in duration and that has audio, and:

* Uploads video to GDrive (default) or YouTube (if set) as unlisted video.
* For GDrive:
    * Selects a GDrive folder from `gdrive-locations.json` based on meeting title.
    * Creates a subfolder named `YYYY-MM-DD <Zoom title>`
    * Places the video, audio, and chat transcript files in that folder on GDrive.
* For YouTube:
    * sets video title to be `<Zoom title> - Mmm DD, YYYY` of recorded date
    * sets video license to "Creative Commons - Attribution"
    * sets video category to "Science & Technology"
    * adds video to a default unlisted playlist, "Uploads from Zoom"
    * adds video to a call-specific playlist based on meeting title & topic.
* **deletes** original video file from Zoom (**not** audio or chat log)

This script is run every hour.

You can see the options by running `uv run scripts/upload_zoom_recordings.py --help`.

#### Usage via GitHub Actions

GitHub actions runs the Zoom upload script on a regular schedule. In most cases, you should not need to do anything. To check its status or see logs, click on the “actions” tab for this repository in GitHub.

**For forcing a cloud run on-demand:** Visit [the actions page][zoom-upload-action-runs] and click the “run workflow” button near the top-right. In the popup, select your options and click “run workflow.” (You will need to have the right permissions set to click the button.)

#### Local Usage

##### Setup

Follow the official instructions to [install uv][uv-install]. On Linux and Mac the simplest method is to run:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

…but you can also install using most package managers (e.g. Homebrew on Mac) or a variety of other methods. See Uv’s docs for a complete list of options and instructions.

##### Usage

Copy the `.env.sample` to `.env` for you own local use, then manually fill in the appropriate values. This file holds secret keys to access services like Zoom and GDrive, and its contents should never be shared publicly.

```sh
cp .env.sample .env
vim .env
```

Load the secrets from `.env` into your current environment:

```sh
source .env
```

Additional secrets are stored in encrypted files in this repository. You’ll need to decrypt the appropriate files before running scripts that need them by running:

```sh
openssl aes-256-cbc -k "$EDGI_ZOOM_API_SECRET" -in <filename>.enc -out <filename> -d -md sha256
```

For example, to upload to GDrive, you’ll need to decrypt `.gdrive-upload-credentials.json` and `gdrive-locations.json` by running:

```sh
openssl aes-256-cbc -k "$EDGI_ZOOM_API_SECRET" -in .gdrive-upload-credentials.json.enc -out .gdrive-upload-credentials.json -d -md sha256
openssl aes-256-cbc -k "$EDGI_ZOOM_API_SECRET" -in gdrive-locations.json.enc -out gdrive-locations.json -d -md sha256
```

For more info on authorization or to generate totally new credentials files, see the [“authorization” section][#authorization] below.

Finally, run the script you want. For example, to upload Zoom recordings to GDrive, run:

```sh
uv run scripts/upload_zoom_recordings.py
```

#### Authorization

This script needs authorized access to EDGI’s Zoom account, GDrive, and YouTube account
in order to do its work.

##### Zoom

To access the Zoom API, you have to create a Zoom *app*. Ours is not published,
so it can only be used in EDGI’s Zoom account. For the scripts to access Zoom
through the app, they require 3 values that are stored in environment variables:

1. `EDGI_ZOOM_ACCOUNT_ID`
2. `EDGI_ZOOM_CLIENT_ID`
3. `EDGI_ZOOM_CLIENT_SECRET`

You can find the appropriate values on the app’s “App Credentials” page. You
can get to that by going to the [App Marketplace](https://marketplace.zoom.us),
clicking on “manage” in the top right, and clicking on the app in the list of
“created apps.”

##### Google (YouTube & GDrive)

Google authorization is slightly more complicated. We have a Google Cloud *app*
that represents our scripts. That app must then be authorized by our Google
account(s) to act on their behalf. That authorization expires periodically and
needs to be manually recreated.

- The basic credentials for the app itself are stored (encrypted) in `client_secret.json.enc`.
- The *authorization* for the app to work in GDrive is stored (encrypted) in `.gdrive-upload-credentials.json.enc`.
- The *authorization* for the app to work in YouTube is stored (encrypted) in `.youtube-upload-credentials.json.enc`.

The `upload_zoom_recordings.py` script only uses the last two authorization files when it runs. The first file (the app credentials) is only used to generate new authorization files.

**To generate a new *authorization* file, you can use the `auth.py` script:**

1. Decrypt the `client_secret.json.enc` file:

    ```sh
    # Ensure you have `EDGI_ZOOM_API_SECRET` set to the decryption key.
    openssl aes-256-cbc -d -k "$EDGI_ZOOM_API_SECRET" -in client_secret.json.enc -out client_secret.json -md sha256
    ```

2. Run the authorization script. It will open a browser window to a GDrive or YouTube login page, where you should log into the appropriate EDGI Google account. Then it will ask you to authorize the app. Afterward, you can close the window.

    The first argument specifies which service to generate authorization for:

    ```sh
    uv run scripts/auth.py gdrive
    ```

    Or:

    ```sh
    uv run scripts/auth.py youtube
    ```

    The script should have created a file named `.gdrive-upload-credentials.json` or `.youtube-upload-credentials.json` depending on your arguments.

3. Encrypt the authorization:

    ```sh
    # For GDrive:
    openssl aes-256-cbc -e -k "$EDGI_ZOOM_API_SECRET" -in .gdrive-upload-credentials.json -out .gdrive-upload-credentials.json.enc
    # For YouTube:
    openssl aes-256-cbc -e -k "$EDGI_ZOOM_API_SECRET" -in .youtube-upload-credentials.json -out .youtube-upload-credentials.json.enc
    ```

4. Commit the new authorization to git for later use!

    ```sh
    git add .gdrive-upload-credentials.json.enc
    git add .youtube-upload-credentials.json.enc
    git commit
    git push
    ```

**To get a completely fresh set of credentials for the app** (should generally never be needed):

1. Log into the [Google Cloud Console][gcloud-console] and make sure you are working in the appropriate project (“EDGI Scripts”).

2. In the sidebar, select “APIs & Services,” then “Credentials.”

3. Find the client ID for this app under “OAuth 2.0 Client IDs” and click to edit it.

4. Under “client secrets,” click the “add secret” button to go through the process of creating and downloading a new secret. (You cannot view or re-download an existing secret.)

5. Save the secret to `client_secret.json` in this repository and encrypt the file:

    ```sh
    openssl aes-256-cbc -e -k "$EDGI_ZOOM_API_SECRET" -in client_secret.json -out client_secret.json.enc
    ```

6. Commit the new authorization to git for later use!

    ```sh
    git add client_secret.json.enc
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
[gcloud-console]: https://console.cloud.google.com/
[github-actions]: https://github.com/edgi-govdata-archiving/edgi-scripts/actions
[uv]: https://docs.astral.sh/uv/
[uv-install]: https://docs.astral.sh/uv/getting-started/installation/
[zoom-upload-action-runs]: https://github.com/edgi-govdata-archiving/edgi-scripts/actions/workflows/zoom-upload.yml
[zoom-upload-action-badge]: https://github.com/edgi-govdata-archiving/edgi-scripts/actions/workflows/zoom-upload.yml/badge.svg?event=schedule
