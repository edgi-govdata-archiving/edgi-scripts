# EDGI Scripts

This is a repository for scripts that are part of EDGI's digital
infrastructure.

These scripts are usually intended to be run regularly in an automated
fashion

## Table of Contents

- [Technologies Used](#technologies-used)
- [Script Catalog](#script-catalog)

## Technologies Used

* [**CircleCI.**][circleci] A script-running service
  that [runs scheduled tasks][circleci-cron] for us in the cloud.

## Script Catalog

### Backup to Internet Archive: `archive.sh`

This script is used to run periodically and ensure that recent copies of
the EDGI website are backed up to the Internet Archive.

**Usage**

```
bash scripts/archive.sh envirodatagov.org
```

### Zoom-to-YouTube Uploader: `upload_zoom_recordings.py` and `auth.py`

This script cycles through Zoom cloud recordings and for each:

* uploads video to youtube as unlisted video
* adds it to a default playlist (which happens to be unlisted)
* sets video title to be `<Zoom title> - Mmm DD, YYYY` of recorded date
* Adds video to call-specific playlist based on meeting title:
  * "Website Monitoring" (alternatively, "Web Mon" or "WM")
  * "Data Together"
  * "Community Call"
* **deletes** original video file from Zoom (**not** audio or chat log)

Note: the script isn't smart enough to detect duplicate videos being
uploaded more than once, but YouTube will recognize and disable them
after upload

#### Usage via CircleCI

[![Run scripts](https://img.shields.io/badge/scheduled%20scripts-RUN-44cc11.svg)][circleci-proj]
[![CircleCI Status](https://img.shields.io/circleci/project/github/edgi-govdata-archiving/edgi-scripts.svg?label=CircleCI)][circleci-proj]

There is actually no need to run this script locally, as we have it
automatically running in the cloud on CircleCI (service explained
above) **every 15 minutes**.

**For forcing a cloud run on-demand:** Visit [our project page on the
CircleCI platform][circleci-proj], and click the "Rerun job with SSH"
button on the latest build page. (You will need to have push access on
the repo itself.)

* We added our secret environment variables, (`EDGI_ZOOM_API_KEY` and
  `EDGI_ZOOM_API_SECRET`), to the [CircleCI configuration
file][circleci-config1] using the [documented method of encrypting
secrets][circleci-envvars].
* Using the [manual encryption method (OpenSSL
  variant)][circleci-encfile], we encrypted the secret Google-related JSON
files, (`client_secret.json` and `.youtube-upload-credentials.json`). We
used the above `EDGI_ZOOM_API_SECRET` as the password, since that's a
secret that CircleCI already knows. We stored the encrypted versions of
these two JSON files in the repo. We added a line to the [CircleCI
config][circleci-config2] to decrypt them for use when running in the
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

**Usage**

```
workon edgi-scripts
pip install -r requirements.txt

# Copy client_secret.json to repo root dir. This is downloaded from
# Google API Console, and will need to be renamed.
# See: https://github.com/tokland/youtube-upload#authentication

# Authorize YouTube app with EDGI account.
# This will need to be done from a system with a windowed browser (ie.
# not a server). It will generate a file named
# `.youtube-upload-credentials.json` in the repo root dir. If running the
# script on a server is required, you will # need to transfer this file
# from your # workstation onto the server.
python scripts/auth.py

# Prepare to download all videos from Zoom
# See: https://zoom.us/developer/api/credential
export EDGI_ZOOM_API_KEY=xxxxxxx
export EDGI_ZOOM_API_SECRET=xxxxxxxx

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
[circleci]: https://circleci.com/docs/1.0/introduction/
[circleci-cron]: https://support.circleci.com/hc/en-us/articles/115015481128-Scheduling-jobs-cron-for-builds-
[circleci-envvars]: https://circleci.com/docs/1.0/environment-variables/#setting-environment-variables-for-all-commands-without-adding-them-to-git
[circleci-encfile]: https://circleci.com/docs/1.0/environment-variables/#keeping-encrypted-environment-variables-in-source-code
[circleci-config1]: https://github.com/edgi-govdata-archiving/edgi-scripts/blob/master/.circleci/config.yml
[circleci-config2]: https://github.com/edgi-govdata-archiving/edgi-scripts/blob/master/.circleci/config.yml
[circleci-proj]: https://circleci.com/gh/edgi-govdata-archiving/edgi-scripts
