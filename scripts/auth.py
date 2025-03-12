from argparse import ArgumentParser
from google_auth_oauthlib.flow import InstalledAppFlow
from lib.gdrive import (DEFAULT_CREDENTIALS_FILE as GDRIVE_CREDENTIALS_FILE,
                        SCOPES as GDRIVE_SCOPES)
from lib.youtube import (DEFAULT_CREDENTIALS_FILE as YOUTUBE_CREDENTIALS_FILE,
                         SCOPES as YOUTUBE_SCOPES)


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


def get_credentials(scopes: list[str]):
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=scopes
    )
    flow.run_local_server()
    return flow.credentials


def main(service: str):
    match service:
        case 'youtube':
            credentials_file = YOUTUBE_CREDENTIALS_FILE
            scopes = YOUTUBE_SCOPES
        case 'gdrive':
            credentials_file = GDRIVE_CREDENTIALS_FILE
            scopes = GDRIVE_SCOPES
        case _:
            raise ValueError(f'Unknown service type: "{service}"')

    credentials = get_credentials(scopes)
    with open(credentials_file, 'w+') as file:
        file.write(credentials.to_json())
        print(f'Wrote new credentials to {credentials_file}.')


if __name__ == '__main__':
    parser = ArgumentParser(description='(Re)authorize access to remote '
                                        'services. This program will create '
                                        'or update files named '
                                        '`.<service>-upload-credentials`.')
    parser.add_argument('service', choices=('gdrive', 'youtube'),
                        default='gdrive',
                        help='Which service to update credentials for.')
    options = parser.parse_args()
    main(options.service)
