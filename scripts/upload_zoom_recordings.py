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

from argparse import ArgumentParser
from datetime import datetime, date, timedelta, timezone
import dateutil.parser
import json
import os
import re
import requests
import subprocess
import sys
import tempfile
from typing import Dict
from urllib.parse import urlsplit
from googleapiclient.http import MediaFileUpload
from zoomus.util import encode_uuid
from lib.constants import MEDIA_TYPE_FOR_EXTENSION, VIDEO_CATEGORY_IDS, ZOOM_ROLES
from lib.youtube import get_youtube_client, upload_video, add_video_to_playlist, validate_youtube_credentials
from lib.gdrive import get_gdrive_client, validate_gdrive_credentials, ensure_folder, is_trashed
from lib.zoom import FancyZoom, ZoomError

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


def fix_date(date_string: str) -> str:
    date = date_string
    index = date.find('Z')
    date = date[:index] + '.0' + date[index:]

    return date


def pretty_date(date_string: str) -> str:
    return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ').strftime('%b %-d, %Y')


def download_zoom_file(client: FancyZoom, url: str, download_directory: str) -> str:
    # Note the token info in the client isn't really *public*, but it's
    # not explicitly private, either. Use `config[]` syntax instead of
    # `config.get()` so we get an exception if things have changed and
    # this data is no longer available.
    r = requests.get(url, stream=True, headers={
        'Authorization': f'Bearer {client.config['token']}'
    })
    r.raise_for_status()
    resolved_url = r.url
    filename = os.path.basename(urlsplit(resolved_url).path)
    filepath = os.path.join(download_directory, filename)
    if os.path.exists(filepath):
        r.close()
        return
    with open(filepath, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)

    return filepath


def meeting_had_no_participants(client: FancyZoom, meeting: Dict) -> bool:
    participants = client.past_meeting.get_participants(meeting_id=meeting['uuid'])['participants']

    return all(
        any(p.search(u['name']) for p in ZOOM_IGNORE_USER_NAMES)
        for u in participants
    )


def recording_status(meeting: Dict) -> str:
    for file in meeting['recording_files']:
        if file['recording_end'] == '':
            return 'ongoing'
        elif file['status'] != 'completed':
            return 'processing'

    return 'ready'


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


def cli_datetime(datetime_string) -> datetime:
    raw = datetime_string.strip()
    delta = re.match(r'^(\+?)(\d+)([dhm])$', raw)
    if delta:
        unit = {'d': 'days', 'h': 'hours', 'm': 'minutes'}[delta.group(3)]
        value = float(delta.group(2))
        if delta.group(1) != '+':
            value *= -1
        return datetime.now(timezone.utc) + timedelta(**{unit: value})

    parsed = dateutil.parser.isoparse(raw)
    # If it's a date, treat it as UTC.
    if re.match(r'^\d{4}-\d\d-\d\d$', raw):
        return parsed.replace(tzinfo=timezone.utc)
    else:
        return parsed.astimezone(timezone.utc)


def save_to_youtube(youtube, meeting: dict, filepath: str, dry_run: bool) -> None:
    recording_date = fix_date(meeting['start_time'])
    title = f'{meeting["topic"]} - {pretty_date(meeting["start_time"])}'

    print(f'    Uploading {filepath}\n      {title=}\n      {recording_date=}')
    if not dry_run:
        video_id = upload_video(youtube,
                                filepath,
                                title=title,
                                category=VIDEO_CATEGORY_IDS["Science & Technology"],
                                license=DEFAULT_VIDEO_LICENSE,
                                recording_date=recording_date,
                                privacy_status='unlisted')

    # Add all videos to default playlist
    print('    Adding to main playlist: Uploads from Zoom')
    if not dry_run:
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
        if not dry_run:
            add_video_to_playlist(youtube, video_id, title=playlist_name, privacy='unlisted')

    # TODO: save the chat log transcript in a comment on the video.


def save_to_gdrive(client, meeting: dict, filepath: str, dry_run: bool,
                   zoom_client: ZoomClient, tempdir: str) -> None:
    recording_date = dateutil.parser.isoparse(meeting['start_time'])

    with open('gdrive-locations.json') as file:
        location_options = json.load(file)

    topic = meeting['topic']
    if re.search(r'\bac meeting', topic, flags=re.IGNORECASE):
        location = location_options['ac']
    elif re.search(r'\beew\b', topic, flags=re.IGNORECASE):
        location = location_options['eew']
    elif 'all-edgi' in topic.lower():
        location = location_options['all_edgi']
    else:
        location = location_options['default']

    folder_id = location['folder']
    if is_trashed(client, folder_id):
        raise RuntimeError(f'Cannot upload to GDrive folder "{folder_id}"; it is in the trash!')

    if location['subfolder_pattern']:
        subfolder_name = location['subfolder_pattern'].format(year=recording_date.year)
        if not dry_run:
            folder_id = ensure_folder(client, location['folder'], subfolder_name)

    iso_date = recording_date.strftime('%Y-%m-%d')
    meeting_name = f'{iso_date} {topic}'
    print(f'    Creating meeting folder "{meeting_name}" in https://drive.google.com/drive/folders/{folder_id} ...')
    if not dry_run:
        meeting_folder = ensure_folder(client, folder_id, meeting_name)

    # Upload files to folder_id
    upload_name = f'{meeting_name}.mp4'
    print(f'    Uploading {filepath}\n      {upload_name=}')
    if not dry_run:
        # TODO: improve resumability by following the suggestions around error
        # handling at the end of this doc:
        # https://github.com/googleapis/google-api-python-client/blob/main/docs/media.md
        file_info = {'name': f'{meeting_name}.mp4', 'parents': [meeting_folder]}
        media = MediaFileUpload(filepath, mimetype='video/mp4', resumable=True)
        file = (
            client.files()
            .create(body=file_info, media_body=media, fields="id")
            .execute()
        )

    for file in meeting['recording_files']:
        download_url = file['download_url']
        extension = file['file_extension'].lower()
        upload_name = None
        file_info = None
        match file['file_type'].lower():
            case 'mp4':
                # We are already handling this file; nothing to do here.
                pass
            case 'm4a':
                upload_name = f'{meeting_name} (audio).{extension}'
            case 'chat':
                upload_name = f'{meeting_name} (chat).{extension}'
            case 'cc':
                upload_name = f'{meeting_name} (transcript).{extension}'
            case filetype:
                # Print warning about unknown file type
                print(f'    ⚠️ Unknown file type for Zoom recording: "{filetype}"')
                print('      Nothing uploaded for this file.')
                continue

        if upload_name:
            media_type = MEDIA_TYPE_FOR_EXTENSION.get(extension)
            if not media_type:
                raise ValueError(f'No known media type for file extension "{extension}"')

            filepath = download_zoom_file(zoom_client, download_url, tempdir)
            print(f'    Uploading {filepath}\n      {upload_name=}')
            if not dry_run:
                file_info = {'name': upload_name, 'parents': [meeting_folder]}
                media = MediaFileUpload(filepath, mimetype=media_type, resumable=True)
                file = (
                    client.files()
                    .create(body=file_info, media_body=media, fields="id")
                    .execute()
                )


def main():
    parser = ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Do not upload recordings.')
    parser.add_argument('--from', type=cli_datetime,
                        default=cli_datetime('3d'), dest='from_time',
                        help='Look for recordings after this date/time. '
                             'Can be an ISO date or time ("2025-01-01") or a '
                             'number of days/hours/minutes ago ("5d" = 5 days '
                             'ago) or from now ("+5d" = 5 days from now).')
    parser.add_argument('--to', type=cli_datetime,
                        default=cli_datetime('+1d'), dest='to_time',
                        help='Look for recordings before this date/time. '
                             'Can be an ISO date or time ("2025-01-01") or a '
                             'number of days/hours/minutes ago ("5d" = 5 days '
                             'ago) or from now ("+5d" = 5 days from now).')
    parser.add_argument('--service', choices=('gdrive', 'youtube'),
                        default='gdrive',
                        help='Which service to upload recordings to.')
    args = parser.parse_args()

    dry_run = args.dry_run or DRY_RUN
    if dry_run:
        print('⚠️ This is a dry run! Videos will not actually be uploaded.\n')

    match args.service:
        case 'gdrive':
            upload_client = get_gdrive_client()
            valid = validate_gdrive_credentials(upload_client)
        case 'youtube':
            upload_client = get_youtube_client()
            valid = validate_youtube_credentials(upload_client)
        case _:
            print(f'Unknown service type: "{args.service}"')
            return sys.exit(1)

    if not valid:
        print(f'The credentials for {args.service} were not valid!')
        print('Please use `python scripts/auth.py` to re-authorize.')
        return sys.exit(1)

    zoom = FancyZoom(ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET, ZOOM_ACCOUNT_ID)

    # Official meeting recordings we will upload belong to the account owner.
    zoom_user_id = zoom.user.list(role_id=ZOOM_ROLES['owner'])['users'][0]['id']

    with tempfile.TemporaryDirectory() as tmpdirname:
        print(f'Creating tmp dir: {tmpdirname}\n')

        print('Looking for videos to upload between '
              f'{args.from_time} and {args.to_time}...')
        meetings = zoom.recording.list(
            user_id=zoom_user_id,
            start=args.from_time,
            end=args.to_time
        )['meetings']
        meetings = sorted(meetings, key=lambda m: m['start_time'])
        # Filter recordings less than 1 minute
        meetings = filter(lambda m: m['duration'] > 1, meetings)
        for meeting in meetings:
            print(f'Processing meeting: {meeting["topic"]} from {meeting["start_time"]} (ID: "{meeting['uuid']}")')

            # 3. filter by criteria (no-op for now)
            if meeting['topic'] not in MEETINGS_TO_RECORD and DO_FILTER:
                print('  Skipping: meeting not in topic list.')
                continue

            status = recording_status(meeting)
            if status != 'ready':
                print(f'  Skipping: recording is still {status}.')
                continue

            if meeting_had_no_participants(zoom, meeting):
                print('  Deleting recording: nobody attended this meeting.')
                if not dry_run:
                    try:
                        zoom.recording.delete(meeting_id=encode_uuid(meeting['uuid']), action='trash')
                        print('  🗑️ Deleted recording.')
                    except ZoomError as error:
                        print(f'  ❌ {error}')
                continue

            # FIXME: we now want to upload all files to gdrive
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
                    if args.service == 'gdrive':
                        save_to_gdrive(upload_client, meeting, filepath, dry_run, zoom, tmpdirname)
                    elif args.service == 'youtube':
                        save_to_youtube(upload_client, meeting, filepath, dry_run)
                else:
                    print('    Skipping upload: video was silent (no mics were on).')

                if ZOOM_DELETE_AFTER_UPLOAD and not dry_run:
                    # Just delete the video for now, since that takes the most storage space.
                    try:
                        zoom.recording.delete_single_recording(
                            meeting_id=encode_uuid(file['meeting_id']),
                            recording_id=file['id'],
                            action='trash'
                        )
                        print(f'  🗑️ Deleted {file["file_type"]} file from Zoom for recording: {meeting["topic"]}')
                    except ZoomError as error:
                        print(f'  ❌ {error}')


if __name__ == '__main__':
    main()
