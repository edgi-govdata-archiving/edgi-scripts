
from functools import wraps
from typing import Dict
from urllib.parse import urlsplit
import os.path
import requests
from requests import Response
from zoomus import ZoomClient


ZOOM_DOCS_URL = 'https://developers.zoom.us/docs/api/'


class ZoomError(Exception):
    response: Response
    data: Dict
    code: int = 0
    message: str

    def __init__(self, response, message=None):
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


class ZoomResponse:
    response: Response
    _data: Dict = None

    def __init__(self, response: Response):
        self.response = response

    def __getitem__(self, name):
        return self.data[name]

    @property
    def data(self):
        if self._data is None:
            self._data = self.response.json()

        return self._data

    @property
    def text(self):
        return self.response.text

    def raise_for_status(self):
        self.raise_for_response(self.response)

    @classmethod
    def is_error(cls, response: Response) -> bool:
        return response.status_code >= 400

    @classmethod
    def raise_for_response(cls, response: Response):
        if cls.is_error(response):
            raise ZoomError(response)


def wrap_method_with_parsing(original):
    @wraps(original)
    def wrapper(*args, **kwargs):
        result = original(*args, **kwargs)
        if isinstance(result, Response):
            result = ZoomResponse(result)
            result.raise_for_status()

        return result

    return wrapper


def wrap_component_with_parsing(component):
    for name in dir(component):
        if not name.startswith('_'):
            original = getattr(component, name)
            if callable(original):
                setattr(component, name, wrap_method_with_parsing(original))


class FancyZoom(ZoomClient):
    """
    Wraps a zoomus ZoomClient so that nice exception objects are raised for bad
    responses and good JSON responses are pre-parsed.

    Examples
    --------
    >>> instance = FancyZoon(CLIENT_ID, CLIENT_SECRET, ACCOUNT_ID)

    Get a user by ID. The response data is readily available:

    >>> instance.user.get(id='abc123')['id'] == 'abc123'

    Raises an exception for errors instead of returning a response object:

    >>> try:
    >>>     client.user.get(id='bad_id')
    >>> except ZoomError as error:
    >>>     error.response.status_code == 404
    >>>     error.code == 1001
    >>>     error.message == 'User does not exist: bad_id'
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for component in self.components.values():
            wrap_component_with_parsing(component)

    def get_file(self, url: str) -> Response:
        # Note the token info in the client isn't really *public*, but it's
        # not explicitly private, either. Use `config[]` syntax instead of
        # `config.get()` so we get an exception if things have changed and
        # this data is no longer available.
        response = requests.get(url, stream=True, headers={
            'Authorization': f'Bearer {self.config['token']}'
        })
        ZoomResponse.raise_for_response(response)
        return response

    def download_file(self, url: str, download_directory: str) -> str:
        response = self.get_file(url)
        resolved_url = response.url
        filename = os.path.basename(urlsplit(resolved_url).path)
        filepath = os.path.join(download_directory, filename)
        if os.path.exists(filepath):
            response.close()
            return

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)

        return filepath
