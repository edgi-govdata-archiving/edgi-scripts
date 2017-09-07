# EDGI Scripts

This is an experimental repository for scripts that make up part of EDGI
digital infrastructure.

At some point in the future, these will likely be run regularly and
on-demand as part of [a visual script-runner
tool](https://github.com/edgi-govdata-archiving/overview/issues/149).

## Zoom-YouTube Uploader

This script cycles through Zoom cloud recordings and for each:

* uploads video to youtube as unlisted video
* adds it to a default playlist (which happens to be unlisted)
* sets video title to be `<title> - Mmm DD, YYYY` of recorded date
* **deletes** original video file from Zoom (**not** audio or chat log)
* stupidly allows duplicates, but YouTube will recognize and disable
  them after upload

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
