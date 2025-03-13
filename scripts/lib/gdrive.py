from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
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

FOLDER_MIME_TYPE = 'application/vnd.google-apps.folder'


# Create client from stored authorization credentials.
def get_gdrive_client(credentials_path: str = DEFAULT_CREDENTIALS_FILE):
    credentials = Credentials.from_authorized_user_file(credentials_path)
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


def ensure_folder(client, parent: str, name: str) -> str:
    """
    Create a folder with the given name if it does not exist. Returns the
    folder's ID.
    """
    # You can't just list a folder's files -- there is only search.
    # Docs: https://developers.google.com/drive/api/guides/search-files
    found = client.files().list(
        q=f"'{parent}' in parents and mimeType = '{FOLDER_MIME_TYPE}' and name = '{name}' and trashed = false",
        fields="nextPageToken, files(id, name)",
    ).execute()
    if len(found['files']):
        return found['files'][0]['id']

    info = {
        'name': name,
        'mimeType': FOLDER_MIME_TYPE,
        'parents': [parent],
    }
    subfolder = client.files().create(body=info, fields="id").execute()
    return subfolder['id']


def is_trashed(client, file_id: str) -> bool:
    """
    Determine if a file/folder is in the trash.
    There is a weird edge case this does *not* account for: if a file is added
    to a folder *after* the folder was put in the trash, the file is not marked
    as trashed (even though it effectivly is... I think).
    """
    return client.files().get(fileId=file_id, fields='id, trashed')['trashed']
