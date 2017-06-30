#!/usr/bin/env python

import json
import os
import requests
import tempfile
from urllib.parse import urlparse
from zoomus import ZoomClient

ZOOM_API_KEY = os.environ['EDGI_ZOOM_API_KEY']
ZOOM_API_SECRET = os.environ['EDGI_ZOOM_API_SECRET']

MEETINGS_TO_RECORD = ['EDGI Community Standup']

client = ZoomClient(ZOOM_API_KEY, ZOOM_API_SECRET)

# Assumes first id is main account
user_id = json.loads(client.user.list().text)['users'][0]['id']

def download_file(url, download_path):
    r = requests.get(url, stream=True)
    resolved_url = r.url
    filename = urlparse(resolved_url).path.split('/')[-1]
    filepath = os.path.join(download_path, filename)
    if os.path.exists(filepath):
        r.close()
        return
    with open(filepath, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)

DO_FILTER = False

with tempfile.TemporaryDirectory() as tmpdirname:
    print('Creating tmp dir: ' + tmpdirname)
    for meeting in json.loads(client.recording.list(host_id=user_id).text)['meetings']:
        print('Processing recording: ' + meeting['topic'] + ' from ' + meeting['start_time'])
        if meeting['topic'] not in MEETINGS_TO_RECORD and DO_FILTER:
            print('Skipping...')
            continue

        print('Recording is permitted for upload!')
        for file in meeting['recording_files']:
            if file['file_type'].lower() == 'mp4':
                url = file['download_url']
                print('Download from ' + url + ' ...')
                download_file(url, tmpdirname)

# 1. get zoom user id for host id
# 2. get zoom meetings
# 3. filter by criteria
# 4. get recordings for filtered meetings
# 6. get youtube video listing from youtube
# 7. ensure no video exists with same properties (length)
# 8. if not, upload to youtube as unlisted
