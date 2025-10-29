from enum import Enum, StrEnum, auto
import os.path
import requests
from requests import Response
from zoomus import ZoomClient
from urllib.parse import urlsplit


ZOOM_DOCS_URL = 'https://developers.zoom.us/docs/api/'


class RecordingStatus(Enum):
    ONGOING = auto()
    PROCESSING = auto()
    READY = auto()

    @staticmethod
    def from_meeting(meeting: dict) -> 'RecordingStatus':
        for file in meeting['recording_files']:
            if file['recording_end'] == '':
                return RecordingStatus.ONGOING
            elif file['status'] != 'completed':
                return RecordingStatus.PROCESSING

        return RecordingStatus.READY


class ZoomRole(StrEnum):
    """
    Built-in user roles for Zoom. Accounts can also have custom roles with
    more complex ID strings that are not listed here.
    """
    OWNER = '0'
    ADMIN = '1'
    MEMBER = '2'


class ZoomError(Exception):
    response: Response
    data: dict
    code: int = 0
    message: str

    def __init__(self, response: Response, message: str | None = None):
        self.response = response
        try:
            self.data = response.json()
        except Exception:
            self.data = {}

        self.message = message or self.data.pop('message', 'Zoom API error')
        self.code = self.data.pop('code', 0)
        super().__init__(
            f'{self.message} '
            f'(code={self.code}, http_status={self.response.status_code}) '
            f'Check the docs for details: {ZOOM_DOCS_URL}.'
        )


def raise_for_status(response: Response) -> None:
    """Raise ``ZoomError`` if the response has a bad status code."""
    if response.status_code >= 400:
        raise ZoomError(response)


def parse_zoom(response: Response) -> dict:
    """Parse a response from the Zoom API as a dict or raise ``ZoomError``."""
    raise_for_status(response)
    return response.json()


def download_zoom_file(client: ZoomClient, url: str, download_directory: str) -> str:
    # Note the token info in the client isn't really *public*, but it's
    # not explicitly private, either. Use `config[]` syntax instead of
    # `config.get()` so we get an exception if things have changed and
    # this data is no longer available.
    r = requests.get(url, stream=True, headers={
        'Authorization': f'Bearer {client.config['token']}'
    })
    raise_for_status(r)
    resolved_url = r.url
    filename = os.path.basename(urlsplit(resolved_url).path)
    filepath = os.path.join(download_directory, filename)
    if os.path.exists(filepath):
        r.close()
        return filepath

    with open(filepath, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)

    return filepath
