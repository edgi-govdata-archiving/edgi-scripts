# EDGI Scripts

This is a repository for scripts that are part of EDGI's digital
infrastructure.

These scripts are usually intended to be run regularly in an automated
fashion

## Table of Contents

- [Technologies Used](#technologies-used)
- [Script Catalog](#script-catalog)

## Technologies Used

* [**TravisCI.**][travis] A community-maintained script-running service
  that [runs scheduled tasks][travis-cron] for us in the cloud.

## Script Catalog

### Backup to Internet Archive: `archive.sh`

This script is used to run periodically and ensure that recent copies of
the EDGI website are backed up to the Internet Archive.

**Usage**

```
bash scripts/archive.sh envirodatagov.org
```

## Zoom-to-YouTube Uploader: `upload_zoom_recordings.py` and `auth.py`

This script cycles through Zoom cloud recordings and for each:

* uploads video to youtube as unlisted video
* adds it to a default playlist (which happens to be unlisted)
* sets video title to be `<Zoom title> - Mmm DD, YYYY` of recorded date
* **deletes** original video file from Zoom (**not** audio or chat log)

Note: the script isn't smart enough to detect duplicate videos being
uploaded more than once, but YouTube will recognize and disable them
after upload

**Usage via TravisCI**
There is actually no need to run this script locally, as we have it
running daily on TravisCI (service explained above).

* We added our secret environment variables, (`EDGI_ZOOM_API_KEY` and
  `EDGI_ZOOM_API_SECRET`), to the [travis configuration
file][travis-config1] using the [documented method of encrypting
secrets][travis-enc].
* Using the [manual encryption method (OpenSSL
  variant)][travis-encfile], we encrypted the secret Google-related JSON
files, (`client_secret.json` and `.youtube-upload-credentials.json`). We
used the above `EDGI_ZOOM_API_SECRET` as the password, since that's a
secret that Travis already knows. We stored the encrypted versions of
these two JSON files in the repo. We added a line to the [travis
config][travis-config2] to decrypt them for use when running in the
cloud.

**For automatic runs of the script:** It kicks off daily around 6am ET.

**For manual runs of the script:** Visit [our project page on the Travis
platform][travis-proj], and click the "Restart build" button.

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

# Authorize YouTube app with EDGI account
# This will need to be done from a system with a windowed browser (ie.
# not a server). If running the script on a server is required, you will
# need to transfer the `.youtube-upload-credentials.json` file from your
# workstation onto the server.
python scripts/auth.py

# Prepare to download all videos from Zoom
# See: https://zoom.us/developer/api/credential
export EDGI_ZOOM_API_KEY=xxxxxxx
export EDGI_ZOOM_API_SECRET=xxxxxxxx

# Download and upload files from Zoom
python scripts/upload_zoom_recordings.py
```

# Contributing Guidelines

We love improvements to our tools! EDGI has general [guidelines for
contributing](https://github.com/edgi-govdata-archiving/overview/blob/master/CONTRIBUTING.md)
to all of our organizational repos.

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
[travis]: https://docs.travis-ci.com/user/for-beginners/
[travis-cron]: https://blog.travis-ci.com/2016-12-06-the-crons-are-here
[travis-enc]: https://docs.travis-ci.com/user/encryption-keys/
[travis-encfile]: https://docs.travis-ci.com/user/encrypting-files/#Manual-Encryption
[travis-config1]: https://github.com/edgi-govdata-archiving/edgi-scripts/blob/travis-cron/.travis.yml#L8-L11
[travis-config2]: https://github.com/edgi-govdata-archiving/edgi-scripts/blob/travis-cron/.travis.yml#L14-L15
[travis-proj]: https://travis-ci.org/edgi-govdata-archiving/edgi-scripts
