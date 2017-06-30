# EDGI Scripts

## Zoom-YouTube Uploader

Requirements:

* `virtualenvwrapper.sh`

```
mkvirtualenv edgi-scripts --python=`which python3`
workon edgi-scripts
pip install -r requirements.txt

# Prepare to download all videos from Zoom
# See: https://zoom.us/developer/api/credential
export EDGI_ZOOM_API_KEY=xxxxxxx
export EDGI_ZOOM_API_SECRET=xxxxxxxx

# Download files from Zoom
python scripts/upload_zoom_recordings.py

# Prepare to upload to YouTube
# See: https://github.com/tokland/youtube-upload#authentication

# Upload each file to YouTube
youtube-upload --title="My Title" GMT20170518-223447_EDGI-Commu_640x360.mp4
```
