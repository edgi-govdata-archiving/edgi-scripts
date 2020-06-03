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
#     This script expects one file to be available to enable YouTube upload:
#
#     * `.youtube-upload-credentials.json`
#
#     See README for how to generate this files.

from datetime import datetime
import functools
import json
import os
import re
import requests
from subprocess import check_output, CalledProcessError, PIPE
import sys
import tempfile
from urllib.parse import urlparse
from zoomus import ZoomClient
from lib.constants import USER_TYPES, VIDEO_CATEGORY_IDS
from lib.youtube import get_youtube_client, upload_video, add_video_to_playlist
from types import SimpleNamespace

YOUTUBE_CREDENTIALS_PATH = '.youtube-upload-credentials.json'
ZOOM_API_KEY = os.environ['EDGI_ZOOM_API_KEY']
ZOOM_API_SECRET = os.environ['EDGI_ZOOM_API_SECRET']

def is_truthy(x): return x.lower() in ['true', '1', 'y', 'yes']
ZOOM_DELETE_AFTER_UPLOAD = is_truthy(os.environ.get('EDGI_ZOOM_DELETE_AFTER_UPLOAD', ''))

MEETINGS_TO_RECORD = ['EDGI Community Standup']
DEFAULT_YOUTUBE_PLAYLIST = 'Uploads from Zoom'
DEFAULT_YOUTUBE_CATEGORY = 'Science & Technology'
DEFAULT_VIDEO_LICENSE = 'creativeCommon'
DO_FILTER = False

client = ZoomClient(ZOOM_API_KEY, ZOOM_API_SECRET)

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

def download_file(url, download_path, query=None):
    r = requests.get(url, params=query, stream=True)
    r.raise_for_status()
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

def main():
    youtube = get_youtube_client(YOUTUBE_CREDENTIALS_PATH)
    with tempfile.TemporaryDirectory() as tmpdirname:
        print('Creating tmp dir: ' + tmpdirname)
        meetings = client.recording.list(user_id=user_id).json()['meetings']
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
                # Note the token info in the client isn't really *public*, but it's
                # not explicitly private, either. Use `config[]` syntax instead of
                # `config.get()` so we get an exception if things have changed and
                # this data is no longer available.
                filepath = download_file(url,
                                        tmpdirname,
                                        query={"access_token": client.config["token"]})
                title = f'{meeting["topic"]} - {pretty_date(meeting["start_time"])}'

                # These characters don't work within Python subprocess commands
                chars_to_strip = '<>'
                title = re.sub('['+chars_to_strip+']', '', title)

                video_id = upload_video(youtube,
                                filepath,
                                title=title,
                                category=VIDEO_CATEGORY_IDS["Science & Technology"],
                                license=DEFAULT_VIDEO_LICENSE,
                                recording_date=fix_date(meeting['start_time']),
                                privacy_status='unlisted')
                
                # Add all videos to default playlist
                print('  Adding to main playlist: Uploads from Zoom')
                add_video_to_playlist(youtube, video_id, title=DEFAULT_YOUTUBE_PLAYLIST, privacy='unlisted')
                
                # Add to additional playlists
                playlist_name = ''
                if any(x in meeting['topic'].lower() for x in ['web mon', 'website monitoring', 'wm']):
                    playlist_name = 'Website Monitoring'

                if 'data together' in meeting['topic'].lower():
                    playlist_name = 'Data Together'

                if 'community call' in meeting['topic'].lower():
                    playlist_name = 'Community Calls'

                if playlist_name:
                    print(f'  Adding to call playlist: {playlist_name}')
                    add_video_to_playlist(youtube, video_id, title=playlist_name, privacy='unlisted')

                if ZOOM_DELETE_AFTER_UPLOAD:
                    # Just delete the video for now, since that takes the most storage space.
                    # We should save the chat log transcript in a comment on the video.
                    
                    # We're using the zoom api directly instead of zoomus, because zoomus only implements
                    # deleting all recorded files related to the meeting using the v2 API, 
                    # while we still want to retain the audio and chat files for backup.
                    url = f'https://api.zoom.us/v2/meetings/{file["meeting_id"]}/recordings/{file["id"]}'
                    querystring = {"action":"trash"}
                    headers = {'authorization': f'Bearer {client.config["token"]}'}
                    response = requests.request("DELETE", url, headers=headers, params=querystring)
                    if response.status_code == 204:
                        print(f'  Deleted {file["file_type"]} file from Zoom for recording: {meeting["topic"]}')
                    else:
                        print(f'  The file could not be deleted. We received this response: {response.status_code}. Please check https://marketplace.zoom.us/docs/api-reference/zoom-api/cloud-recording/recordingdeleteone for what that could mean.')
                    

if __name__ == '__main__':
    main()
