#!/usr/bin/env bash

VENV=edgi-scripts

activate () {
  . $HOME/.virtualenvs/${VENV}/bin/activate
}

activate
python scripts/upload_zoom_recordings.py
youtube-upload --title="Untitled Zoom Call" downloads/GMT20170706-222918_EDGI-Commu_gallery_1280x720.mp4 --client-secrets client_secret_1018754759866-cjn721321m2q0de1cfva11nvjqmdurj1.apps.googleusercontent.com.json --privacy unlisted
