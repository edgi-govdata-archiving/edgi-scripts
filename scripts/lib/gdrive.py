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


# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
SCOPES = [
    'https://www.googleapis.com/auth/drive.metadata.readonly',
    'https://www.googleapis.com/auth/drive.file'
]
DEFAULT_CREDENTIALS_FILE = '.gdrive-upload-credentials.json'
API_SERVICE_NAME = 'drive'
API_VERSION = 'v3'


# Create client from stored authorization credentials.
def get_gdrive_client(credentials_path: str = DEFAULT_CREDENTIALS_FILE):
    credentials = google.oauth2.credentials.Credentials.from_authorized_user_file(credentials_path)
    return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)


def validate_gdrive_credentials(client) -> bool:
    """
    Make a basic API request to validate the given credentials work. Returns a
    boolean indicating whether credentials are valid.
    """
    try:
        (
            client.files()
            .list(pageSize=10, fields="nextPageToken, files(id, name)")
            .execute()
        )
        return True
    except GoogleAuthError:
        return False
