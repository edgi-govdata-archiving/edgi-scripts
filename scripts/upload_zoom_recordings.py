#!/usr/bin/env python
#
# Description:
#
#      This script will download cloud recordings from Zoom Meetings, and
#      upload them to YouTube.
#
# Usage:
#
#      python scripts/upload_zoom_recordings.py
#
# Environment Variables:
#
#     EDGI_ZOOM_API_KEY - See https://developer.zoom.us/me/ (required)
#     EDGI_ZOOM_API_SECRET - See https://developer.zoom.us/me/ (required)
#     EDGI_ZOOM_DELETE_AFTER_UPLOAD - If set to 'true', cloud recording will be
#         deleted after upload to YouTube.
#
# Configuration:
#
#     This script expects two files to be available to enable YouTube upload:
#
#     * `client_secret.json`
#     * `.youtube-upload-credentials.json`
#
#     See README for how to generate these files.

from datetime import datetime
import functools
import json
import os
import re
import requests
import playlists
from subprocess import check_output, CalledProcessError, PIPE
import sys
import tempfile
from urllib.parse import urlparse
from zoomus import ZoomClient
from constants import USER_TYPES

# from youtube_upload import main, playlists
from basic_youtube_upload import get_youtube_client, initialize_upload
from types import SimpleNamespace


ZOOM_API_KEY = os.environ['EDGI_ZOOM_API_KEY']
ZOOM_API_SECRET = os.environ['EDGI_ZOOM_API_SECRET']

def is_truthy(x): return x.lower() in ['true', '1', 'y', 'yes']
ZOOM_DELETE_AFTER_UPLOAD = is_truthy(os.environ.get('EDGI_ZOOM_DELETE_AFTER_UPLOAD', ''))

MEETINGS_TO_RECORD = ['EDGI Community Standup']
DEFAULT_YOUTUBE_PLAYLIST = 'Uploads from Zoom'
DEFAULT_YOUTUBE_CATEGORY = 'Science & Technology'
DEFAULT_VIDEO_LICENSE = 'creativeCommon'

client = ZoomClient(ZOOM_API_KEY, ZOOM_API_SECRET, version=1)

# Get main account, which should be 'pro'
pro_users = [user for user in client.user.list().json()['users'] if user['type'] >= USER_TYPES['pro'] ]
user_id = pro_users[0]['id']

def fix_date(date_string):
    date = date_string
    index = date.find('Z')
    date = date[:index] + '.0' + date[index:]

    return date

def pretty_date(date_string):
    return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ').strftime('%b %-d, %Y')

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

    return filepath

DO_FILTER = False

youtube = get_youtube_client()
with tempfile.TemporaryDirectory() as tmpdirname:
    print('Creating tmp dir: ' + tmpdirname)
    meetings = client.recording.list(host_id=user_id).json()['meetings']
    meetings = sorted(meetings, key=lambda m: m['start_time'])
    # Filter recordings less than 1 minute
    meetings = filter(lambda m: m['duration'] > 1, meetings)
    for meeting in meetings:
        print(f'Processing meeting: {meeting["topic"]} from {meeting["start_time"]}')
        # 3. filter by criteria (no-op for now)
        if meeting['topic'] not in MEETINGS_TO_RECORD and DO_FILTER:
            print('  Skipping...')
            continue
        
        videos = [file for file in meeting['recording_files']
                  if file['file_type'].lower() == 'mp4']
        
        if len(videos) == 0:
            print(f'  No videos to upload: {meeting["topic"]}')
            continue
        elif any((file['file_size'] == 0 for file in videos)):
            print(f'  Meeting still processing: {meeting["topic"]}')
            continue

        print('  Recording is permitted for upload!')
        for file in videos:
            url = file['download_url']
            print(f'  Download from {url}...')
            filepath = download_file(url, tmpdirname)
            title = f'{meeting["topic"]} - {pretty_date(meeting["start_time"])}'

            # These characters don't work within Python subprocess commands
            chars_to_strip = '<>'
            title = re.sub('['+chars_to_strip+']', '', title)

            print('  Adding to main playlist: Uploads from Zoom')
            video_id = initialize_upload(youtube,
                              filepath,
                              title=title,
                              category=28, # TODO: get category by name: DEFAULT_YOUTUBE_CATEGORY,
                              license=DEFAULT_VIDEO_LICENSE,
                              recording_date=fix_date(meeting['start_time']),
                              privacy_status='unlisted')
            
            playlist_name = DEFAULT_YOUTUBE_PLAYLIST

            if any(x in meeting['topic'].lower() for x in ['web mon', 'website monitoring', 'wm']):
                playlist_name = 'Website Monitoring'

            if 'data together' in meeting['topic'].lower():
                playlist_name = 'Data Together'

            if 'community call' in meeting['topic'].lower():
                playlist_name = 'Community Calls'

            if playlist_name:
                print('  Adding to call playlist: {}'.format(playlist_name))
                playlists.add_video_to_playlist(youtube, video_id, title=playlist_name, privacy='unlisted')

            if ZOOM_DELETE_AFTER_UPLOAD:
                # Just delete the video for now, since that takes the most storage space.
                # We should save the chat log transcript in a comment on the video.
                client.recording.delete(meeting_id=file['meeting_id'], file_id=file['id'])
                print("  Deleted {} file from Zoom for recording: {}".format(file['file_type'], meeting['topic']))
