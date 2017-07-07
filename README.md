# EDGI Scripts

This is an experimental repository for scripts that make up part of EDGI
digital infrastructure.

At some point in the future, these will likely be run regularly and
on-demand as part of [a visual script-runner
tool](https://github.com/edgi-govdata-archiving/overview/issues/149).

## Zoom-YouTube Uploader

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

# Copy client_secret.json to repo root dir

# Authorize YouTube app with [EDGI] account
python scripts/auth.py

# Prepare to download all videos from Zoom
# See: https://zoom.us/developer/api/credential
export EDGI_ZOOM_API_KEY=xxxxxxx
export EDGI_ZOOM_API_SECRET=xxxxxxxx

# Download and upload files from Zoom
python scripts/upload_zoom_recordings.py
```
