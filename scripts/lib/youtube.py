#!/usr/bin/python

import argparse
import http.client as httplib
import httplib2
import os
import random
import time
import json
import locale
import sys

import google.oauth2.credentials
from googleapiclient.discovery import build, build_from_document
from googleapiclient.errors import HttpError, UnknownApiNameOrVersion
from googleapiclient.http import MediaFileUpload
from google.auth.exceptions import GoogleAuthError


# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib.NotConnected,
  httplib.IncompleteRead, httplib.ImproperConnectionState,
  httplib.CannotSendRequest, httplib.CannotSendHeader,
  httplib.ResponseNotReady, httplib.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

VALID_PRIVACY_STATUSES = ('public', 'private', 'unlisted')

def debug(obj, fd=sys.stderr):
    """Write obj to standard error."""
    print(obj, file=fd)

def parse_youtube_http_error(error):
    """
    HTTP errors (class `googleapiclient.errors.HttpError`) unfortunately don't
    make their details available in any useful way (!), so we have to do some
    parsing here.

    See how the error class handles parsing here:
    https://github.com/googleapis/google-api-python-client/blob/41144858a766d2a2216af3aaa94c4aa7cd6fbe30/googleapiclient/errors.py#L47-L67
    
    Oddly, it doesn't match up with the format of YouTube errors here:
    https://developers.google.com/youtube/v3/docs/core_errors
    """
    try:
        data = json.loads(error.content.decode("utf-8"))["error"]
        # Ensure every error has `domain`, `reason`, `message`, and `code`. (They
        # should, but just in case...)
        for error in data["errors"]:
            error.setdefault("domain", "")
            error.setdefault("reason", "")
            error.setdefault("message", "")
            error.setdefault("code", data["code"])
        return data
    except (ValueError, KeyError, TypeError):
        return None

# Create client from stored authorization credentials.
def get_youtube_client(credentials_path):
    credentials = google.oauth2.credentials.Credentials.from_authorized_user_file(credentials_path)
    try: 
        return build(API_SERVICE_NAME, API_VERSION, credentials = credentials)
    except UnknownApiNameOrVersion:
        pass
    try: 
        json_path = 'youtube-api-rest.json'
        with open(path_json) as f:
            service = json.load(f)
        
        return build_from_document(service, credentials = credentials)
    except:
        raise


def validate_youtube_credentials(youtube) -> bool:
    """
    Make a basic API request to validate the given credentials work. Returns a
    boolean indicating whether credentials are valid.
    """
    try:
        request = youtube.playlists().list(part='id,contentDetails', mine=True)
        request.execute()
        return True
    except GoogleAuthError:
        return False


def upload_video(youtube, file, title='Test Title', description=None,
                 category=None, tags=None, privacy_status='private',
                 recording_date=None, license=None):
    """
    Parameters
    ----------
    tags : list of str
    """
    metadata = dict(title=title)
    if description:
        metadata['description'] = description
    if tags:
        metadata['tags'] = tags
    if category:
        metadata['categoryId'] = category

    body=dict(
        snippet=metadata,
        status=dict(privacyStatus=privacy_status)
    )

    if recording_date:
        body['recordingDetails'] = dict(recordingDate=recording_date)
    if license:
        body['status']['license'] = license

    # Call the API's videos.insert method to create and upload the video.
    insert_request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        # The chunksize parameter specifies the size of each chunk of data, in
        # bytes, that will be uploaded at a time. Set a higher value for
        # reliable connections as fewer chunks lead to faster uploads. Set a lower
        # value for better recovery on less reliable connections.
        #
        # Setting 'chunksize' equal to -1 in the code below means that the entire
        # file will be uploaded in a single HTTP request. (If the upload fails,
        # it will still be retried where it left off.) This is usually a best
        # practice, but if you're using Python older than 2.6 or if you're
        # running on App Engine, you should set the chunksize to something like
        # 1024 * 1024 (1 megabyte).
        media_body=MediaFileUpload(file, chunksize=-1, resumable=True)
    )

    return resumable_upload(insert_request)

# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(request):
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            debug('Uploading file...')
            status, response = request.next_chunk()
            if response is not None:
                if 'id' in response:
                    debug('Video id "%s" was successfully uploaded.' % response['id'])
                    return response['id']
                else:
                    raise ValueError('The upload failed with an unexpected response: %s' % response)
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = 'A retriable HTTP error %d occurred:\n%s' % (e.resp.status,
                                                                 e.content)
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = 'A retriable error occurred: %s' % e
  
        if error is not None:
            debug(error)
            retry += 1
            if retry > MAX_RETRIES:
                raise ValueError(error)
    
            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            debug('Sleeping %f seconds and then retrying...' % sleep_seconds)
            time.sleep(sleep_seconds)


# Portions of the playlist code came from:
# Author: https://github.com/tokland
# Source: https://github.com/tokland/youtube-upload/blob/master/youtube_upload/playlists.py
# License: GNU/GPLv3

def find_playlist_id(youtube, title):
    """Return users's playlist ID by title (None if not found)"""
    playlists = youtube.playlists()
    request = playlists.list(mine=True, part="id,snippet")
    current_encoding = locale.getpreferredencoding()
    
    while request:
        results = request.execute()
        for item in results["items"]:
            existing_playlist_title = item.get("snippet", {}).get("title")
            if existing_playlist_title == title:
                return item.get("id")
        request = playlists.list_next(request, results)

def create_playlist(youtube, title, privacy):
    """Create a playlist by title and return its ID"""
    debug(f"Creating playlist: {title}")
    response = youtube.playlists().insert(part="snippet,status", body={
        "snippet": {
            "title": title,
        },
        "status": {
            "privacyStatus": privacy,
        }
    }).execute()
    return response.get("id")

def add_video_to_existing_playlist(youtube, playlist_id, video_id):
    """Add video to playlist (by identifier) and return the playlist ID."""
    debug(f"Adding video to playlist: {playlist_id}")

    body = {
        "snippet": {
            "playlistId": playlist_id,
            "position": 0,
            "resourceId": {
                "kind": "youtube#video",
                "videoId": video_id,
            }
        }
    }

    try:
        return youtube.playlistItems().insert(part="snippet",
                                              body=body).execute()
    except HttpError as error:
        parsed = parse_youtube_http_error(error)
        # A "manualSortRequired" error means the playlist is not manually
        # sorted, and it needs to be in order to use "position". So just try
        # again without setting "position" this time. (It's dumb, but the API
        # appears to provide no way to test for this ahead of time.)
        if parsed and any(error["reason"] == "manualSortRequired" for error in parsed["errors"]):
            del body["snippet"]["position"]
            return youtube.playlistItems().insert(part="snippet",
                                                  body=body).execute()
        else:
            raise

def add_video_to_playlist(youtube, video_id, title, privacy="unlisted"):
    """Add video to playlist (by title) and return the full response."""
    playlist_id = (find_playlist_id(youtube, title) or 
                   create_playlist(youtube, title, privacy))
    if playlist_id:
        return add_video_to_existing_playlist(youtube, playlist_id, video_id)
    else:
        debug("Error adding video to playlist")
        