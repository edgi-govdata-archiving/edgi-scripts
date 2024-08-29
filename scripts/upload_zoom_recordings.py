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
#     EDGI_ZOOM_CLIENT_ID - Client ID for the Zoom OAuth app for this script
#     ZOOM_CLIENT_SECRET - Client Secret for the Zoom OAuth app for this script
#     ZOOM_ACCOUNT_ID - Account ID for the Zoom OAuth app for this script
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
import os
import re
import requests
import subprocess
import sys
import tempfile
from typing import Dict
from urllib.parse import urlparse
from zoomus import ZoomClient
from lib.constants import USER_TYPES, VIDEO_CATEGORY_IDS
from lib.youtube import get_youtube_client, upload_video, add_video_to_playlist, validate_youtube_credentials

YOUTUBE_CREDENTIALS_PATH = '.youtube-upload-credentials.json'
ZOOM_CLIENT_ID = os.environ['EDGI_ZOOM_CLIENT_ID']
ZOOM_CLIENT_SECRET = os.environ['EDGI_ZOOM_CLIENT_SECRET']
ZOOM_ACCOUNT_ID = os.environ['EDGI_ZOOM_ACCOUNT_ID']

MEETINGS_TO_RECORD = ['EDGI Community Standup']
DEFAULT_YOUTUBE_PLAYLIST = 'Uploads from Zoom'
DEFAULT_YOUTUBE_CATEGORY = 'Science & Technology'
DEFAULT_VIDEO_LICENSE = 'creativeCommon'
DO_FILTER = False

# Ignore users with names that match these patterns when determining if a
# meeting has any participants and its recordings should be preserved.
ZOOM_IGNORE_USER_NAMES = (
    # The otter.ai notetaker bot is always present in most meetings.
    re.compile(r'Otter\.ai', re.I),
)


def is_truthy(x):
    return x.lower() in ['true', '1', 'y', 'yes']


ZOOM_DELETE_AFTER_UPLOAD = is_truthy(os.environ.get('EDGI_ZOOM_DELETE_AFTER_UPLOAD', ''))
DRY_RUN = is_truthy(os.environ.get('EDGI_DRY_RUN', ''))


class ZoomError(Exception):
    def __init__(self, response, message=None):
        try:
            data = response.json()
        except Exception:
            data = {}

        if not message:
            message = data.pop('message', 'Zoom API error!')

        data['http_status'] = response.status_code
        full_message = f'{message} ({data!r}) Check the docs for details: https://developers.zoom.us/docs/api/.'
        super.__init__(full_message)

    @classmethod
    def is_error(cls, response):
        return response.status_code >= 400

    @classmethod
    def raise_if_error(cls, response, message=None):
        if cls.is_error(response):
            raise cls(response, message)

    @classmethod
    def parse_or_raise(cls, response, message=None) -> Dict:
        cls.raise_if_error(response, message)
        return response.json()


def fix_date(date_string: str) -> str:
    date = date_string
    index = date.find('Z')
    date = date[:index] + '.0' + date[index:]

    return date


def pretty_date(date_string: str) -> str:
    return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ').strftime('%b %-d, %Y')


def download_zoom_file(client: ZoomClient, url: str, download_directory: str) -> str:
    # Note the token info in the client isn't really *public*, but it's
    # not explicitly private, either. Use `config[]` syntax instead of
    # `config.get()` so we get an exception if things have changed and
    # this data is no longer available.
    r = requests.get(url, stream=True, headers={
        'Authorization': f'Bearer {client.config['token']}'
    })
    r.raise_for_status()
    resolved_url = r.url
    filename = urlparse(resolved_url).path.split('/')[-1]
    filepath = os.path.join(download_directory, filename)
    if os.path.exists(filepath):
        r.close()
        return
    with open(filepath, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)

    return filepath


def delete_zoom_recording_file(client: ZoomClient, file):
    """
    Delete a single file from a meeting recording.

    This exists because zoomus only has built in support for deleting a whole
    recording and all its files. However, we often want to delete a particular
    file (e.g. delete the video, but leave the audio or chat transcript).
    """
    response = client.meeting.delete_request(f'/meetings/{file["meeting_id"]}/recordings/{file["id"]}', params={'action': 'trash'})
    if response.status_code != 204:
        raise ZoomError(response)


def meeting_had_no_participants(client: ZoomClient, meeting: Dict) -> bool:
    participants = ZoomError.parse_or_raise(client.past_meeting.get_participants(meeting_id=meeting['uuid']))['participants']

    return all(
        any(p.search(u['name']) for p in ZOOM_IGNORE_USER_NAMES)
        for u in participants
    )


def video_has_audio(file_path: str) -> bool:
    """Detect whether a video file has a non-silent audio track."""
    result = subprocess.run([
        'ffmpeg',
        '-i', file_path,
        # The `ebur128=peak` looks for the peak loudness level of the audio.
        '-af', 'ebur128=peak=true',
        '-f', 'null',
        '-'
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    # No audio track.
    if b'audio:0kib' in result.stdout.lower():
        return False

    # Selent audio. Note that this won't handle things like the low hiss of an
    # empty room, which will report some low decibel level instead of `-inf`.
    # In practice, this covers Zoom recordings where a mic was never turned on.
    # Docs: https://ffmpeg.org/ffmpeg-filters.html#ebur128-1
    if re.search(rb'Peak:\s+-inf', result.stdout):
        return False

    return True


def main():
    if DRY_RUN:
        print('⚠️ This is a dry run! Videos will not actually be uploaded.\n')

    youtube = get_youtube_client(YOUTUBE_CREDENTIALS_PATH)
    if not validate_youtube_credentials(youtube):
        print(f'The credentials in {YOUTUBE_CREDENTIALS_PATH} were not valid!')
        print('Please use `python scripts/auth.py` to re-authorize.')
        return sys.exit(1)

    zoom = ZoomClient(ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET, ZOOM_ACCOUNT_ID)

    # Get main account, which should be 'pro'
    zoom_user_id = next(user['id'] for user in zoom.user.list().json()['users']
                        if user['type'] >= USER_TYPES['pro'])

    with tempfile.TemporaryDirectory() as tmpdirname:
        print(f'Creating tmp dir: {tmpdirname}\n')

        meetings = ZoomError.parse_or_raise(zoom.recording.list(user_id=zoom_user_id))['meetings']
        meetings = sorted(meetings, key=lambda m: m['start_time'])
        # Filter recordings less than 1 minute
        meetings = filter(lambda m: m['duration'] > 1, meetings)
        for meeting in meetings:
            print(f'Processing meeting: {meeting["topic"]} from {meeting["start_time"]} (ID: "{meeting['uuid']}")')

            # 3. filter by criteria (no-op for now)
            if meeting['topic'] not in MEETINGS_TO_RECORD and DO_FILTER:
                print('  Skipping: meeting not in topic list.')
                continue

            if meeting_had_no_participants(zoom, meeting):
                print('  Deleting recording: nobody attended this meeting.')
                if not DRY_RUN:
                    response = zoom.recording.delete(meeting_id=meeting['uuid'], action='trash')
                    if response.status_code < 300:
                        print('  🗑️ Deleted recording.')
                    else:
                        print(f'  ❌ {ZoomError(response)}')
                continue

            videos = [file for file in meeting['recording_files']
                      if file['file_type'].lower() == 'mp4']

            if len(videos) == 0:
                print('  🔹 Skipping: no videos for meeting')
                continue
            elif any((file['file_size'] == 0 for file in videos)):
                print('  🔹 Skipping: meeting still processing')
                continue

            print(f'  {len(videos)} videos to upload...')
            for file in videos:
                url = file['download_url']
                print(f'    Download from {url}...')
                filepath = download_zoom_file(zoom, url, tmpdirname)

                if video_has_audio(filepath):
                    recording_date = fix_date(meeting['start_time'])
                    title = f'{meeting["topic"]} - {pretty_date(meeting["start_time"])}'

                    print(f'    Uploading {filepath}\n      {title=}\n      {recording_date=}')
                    if not DRY_RUN:
                        video_id = upload_video(youtube,
                                                filepath,
                                                title=title,
                                                category=VIDEO_CATEGORY_IDS["Science & Technology"],
                                                license=DEFAULT_VIDEO_LICENSE,
                                                recording_date=recording_date,
                                                privacy_status='unlisted')

                    # Add all videos to default playlist
                    print('    Adding to main playlist: Uploads from Zoom')
                    if not DRY_RUN:
                        add_video_to_playlist(youtube, video_id, title=DEFAULT_YOUTUBE_PLAYLIST, privacy='unlisted')

                    # Add to additional playlists
                    playlist_name = ''
                    if any(x in meeting['topic'].lower() for x in ['web mon', 'website monitoring', 'wm']):
                        playlist_name = 'Website Monitoring'

                    if 'data together' in meeting['topic'].lower():
                        playlist_name = 'Data Together'

                    if 'community call' in meeting['topic'].lower():
                        playlist_name = 'Community Calls'

                    if 'edgi introductions' in meeting['topic'].lower():
                        playlist_name = 'EDGI Introductions'

                    if 'all-edgi' in meeting['topic'].lower():
                        playlist_name = 'All-EDGI Meetings'

                    if playlist_name:
                        print(f'    Adding to call playlist: {playlist_name}')
                        if not DRY_RUN:
                            add_video_to_playlist(youtube, video_id, title=playlist_name, privacy='unlisted')

                    # TODO: save the chat log transcript in a comment on the video.
                else:
                    print('    Skipping upload: video was silent (no mics were on).')

                if ZOOM_DELETE_AFTER_UPLOAD and not DRY_RUN:
                    # Just delete the video for now, since that takes the most storage space.
                    try:
                        delete_zoom_recording_file(zoom, file)
                        print(f'  🗑️ Deleted {file["file_type"]} file from Zoom for recording: {meeting["topic"]}')
                    except ZoomError as error:
                        print(f'  ❌ {error}')


if __name__ == '__main__':
    main()
