from google_auth_oauthlib.flow import InstalledAppFlow

# If modifying these scopes, delete your previously saved credentials
SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl']

# The CLIENT_SECRET_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the {{ Google Cloud Console }} at
# {{ https://cloud.google.com/console }}.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'youtube-upload'
CREDS_FILENAME = '.youtube-upload-credentials.json'

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES
    )
    flow.run_local_server()
    return flow.credentials

def main():
    credentials = get_credentials()
    with open(CREDS_FILENAME, 'w+') as file:
        file.write(credentials.to_json())
        print(f'Wrote new credentials to {CREDS_FILENAME}.')

if __name__ == '__main__':
    main()
