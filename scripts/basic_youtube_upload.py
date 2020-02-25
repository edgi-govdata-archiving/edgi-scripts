#!/usr/bin/python

import argparse
import http.client as httplib
import httplib2
import os
import random
import time

import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow


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

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the {{ Google Cloud Console }} at
# {{ https://cloud.google.com/console }}.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRETS_FILE = 'client_secret.json'

# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

VALID_PRIVACY_STATUSES = ('public', 'private', 'unlisted')


# Authorize the request and store authorization credentials.
def get_authenticated_service(secrets_path):
    flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
    credentials = flow.run_console()
    return build(API_SERVICE_NAME, API_VERSION, credentials = credentials)


def initialize_upload(youtube, file, title='Test Title', description=None,
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

    resumable_upload(insert_request)

# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(request):
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            print('Uploading file...')
            status, response = request.next_chunk()
            if response is not None:
                if 'id' in response:
                    print('Video id "%s" was successfully uploaded.' % response['id'])
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
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
                raise ValueError(error)
    
            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print('Sleeping %f seconds and then retrying...' % sleep_seconds)
            time.sleep(sleep_seconds)


def upload_video(path, youtube_secrets_file, **kwargs):
    youtube = get_authenticated_service(youtube_secrets_file)
    try:
        initialize_upload(youtube, file=path, **kwargs)
    except HttpError as e:
        print(f'An HTTP error {e.resp.status} occurred:\n{e.content}')

def add_video_to_playlist(youtube,videoID,playlistID):
    request = youtube.playlistItems().insert(
        part="snippet",
        body={
          "snippet": {
            "playlistId": playlistID,
            "position": 2,
            "resourceId": {
              "kind": "youtube#video",
              "videoId": videoID
            }
          }
        }
    )
    response = request.execute()

    print(response)

# if __name__ == '__main__':
#   parser = argparse.ArgumentParser()
#   parser.add_argument('--file', required=True, help='Video file to upload')
#   parser.add_argument('--title', help='Video title', default='Test Title')
#   parser.add_argument('--description', help='Video description',
#     default='Test Description')
#   parser.add_argument('--category', default='22',
#     help='Numeric video category. ' +
#       'See https://developers.google.com/youtube/v3/docs/videoCategories/list')
#   parser.add_argument('--keywords', help='Video keywords, comma separated',
#     default='')
#   parser.add_argument('--privacyStatus', choices=VALID_PRIVACY_STATUSES,
#     default='private', help='Video privacy status.')
#   args = parser.parse_args()

#   youtube = get_authenticated_service()

#   try:
#     initialize_upload(youtube, args)
#   except HttpError, e:
#     print 'An HTTP error %d occurred:\n%s' % (e.resp.status, e.content)
