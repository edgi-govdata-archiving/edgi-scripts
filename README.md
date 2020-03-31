# EDGI Scripts

[![Code of Conduct](https://img.shields.io/badge/%E2%9D%A4-code%20of%20conduct-blue.svg?style=flat)](https://github.com/edgi-govdata-archiving/overview/blob/master/CONDUCT.md) [![Run scripts](https://img.shields.io/badge/scheduled%20scripts-RUN-44cc11.svg)][circleci-proj]
[![CircleCI Status](https://img.shields.io/circleci/project/github/edgi-govdata-archiving/edgi-scripts.svg?label=CircleCI)][circleci-proj]

Helper scripts for EDGI's digital infrastructure.

We use this as a catch-all for simple scripts that help with repeating tasks. Many of them run automatically in the cloud.

## Table of Contents

- [Technologies Used](#technologies-used)
- [About These Automated Scripts](#about-these-automated-scripts)
- [Script Catalog](#script-catalog)

## Technologies Used

- **Python >=3.6.** A programming language common in scripting.
- [**Click.**][click] A Python library for writing simple command-line
  tools.
- [**CircleCI.**][circleci] A script-running service that [runs scheduled
  tasks][circleci-cron] for us in the cloud.
  
## About these Automated Scripts

Some of these scripts are automatically at regular intervals,
using CircleCI's "workflow" feature. The schedule is set in the
[`.circleci/config.yml`][circleci-config] file within this repo.

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
* adds video to call-specific playlist based on meeting title:
  * "Website Monitoring" (alternatively, "Web Mon" or "WM")
  * "Data Together"
  * "Community Call"
* **deletes** original video file from Zoom (**not** audio or chat log)

This script is run every 30 minutes.

Note: the script isn't smart enough to detect duplicate videos being
uploaded more than once, but YouTube will recognize and disable them
after upload

#### Usage via CircleCI

**For forcing a cloud run on-demand:** Visit [our project page on the
CircleCI platform][circleci-proj], and click the "Rerun job with SSH"
button on the latest build page. (You will need to have push access on
the repo itself.)

* We added our secret environment variables, (`EDGI_ZOOM_API_KEY`,
  `EDGI_ZOOM_API_SECRET`, `DEFAULT_YOUTUBE_PLAYLIST`), to the [CircleCI configuration
file][circleci-config] using the [documented method of encrypting
secrets][circleci-envvars].
* Using the [manual encryption method (OpenSSL
  variant)][circleci-encfile], we encrypted the secret Google-related JSON
files, (`client_secret.json` and `.youtube-upload-credentials.json`). We
used the above `EDGI_ZOOM_API_SECRET` as the password, since that's a
secret that CircleCI already knows. We stored the encrypted versions of
these two JSON files in the repo. We added a line to the [CircleCI
config][circleci-config] to decrypt them for use when running in the
cloud.

**Setup**

Quick reference for Ubuntu (may vary).

```
apt-get install python python-pip
pip install virtualenvwrapper
echo 'source /usr/local/bin/virtualenvwrapper.sh' >> ~/.bashrc
exec $SHELL
mkvirtualenv edgi-scripts --python=`which python3`
```
Get Python 3.6. This packages makes use of modern Python features and requires Python 3.6+. If you don't have Python 3.6, we recommend using [conda][conda] to install it. (You don't need admin privileges to install or use it, and it won't interfere with any other installations of Python already on your system.)

**Usage**

```
pip install -r requirements.txt

# Copy client_secret.json to repo root dir. This is downloaded from
# Google API Console, and will need to be renamed.
# See: https://github.com/tokland/youtube-upload#setup

# Authorize YouTube app with EDGI account.
# This will need to be done from a system with a windowed browser (ie.
# not a server). It will generate a file named
# `.youtube-upload-credentials.json` in the repo root dir. If running the
# script on a server is required, you will 
# need to transfer this file
# from your workstation onto the server.
python scripts/auth.py

# Prepare to download all videos from Zoom
# See: https://zoom.us/developer/api/credential
export EDGI_ZOOM_API_KEY=xxxxxxx
export EDGI_ZOOM_API_SECRET=xxxxxxxx
export DEFAULT_YOUTUBE_PLAYLIST=xxxxxxx

# Download from Zoom and upload to YouTube
python scripts/upload_zoom_recordings.py
```

# Contributing Guidelines

We love improvements to our tools! EDGI has general [guidelines for
contributing](https://github.com/edgi-govdata-archiving/overview/blob/master/CONTRIBUTING.md)
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
[circleci]: https://circleci.com/docs/1.0/introduction/
[circleci-cron]: https://support.circleci.com/hc/en-us/articles/115015481128-Scheduling-jobs-cron-for-builds-
[circleci-envvars]: https://circleci.com/docs/2.0/env-vars/#notes-on-security
[circleci-encfile]: https://github.com/circleci/encrypted-files
[circleci-config]: https://github.com/edgi-govdata-archiving/edgi-scripts/blob/master/.circleci/config.yml
[circleci-proj]: https://circleci.com/gh/edgi-govdata-archiving/edgi-scripts
[conda]: https://conda.io/miniconda.html