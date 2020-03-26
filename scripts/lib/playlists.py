import googleapiclient
import json
import locale
import sys

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

    ¯\_(ツ)_/¯
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

# TODO: Place playlist_id of PUBLIC playlists into constants.py instead of looking up in youtube
# because that eats some of our quota credits. Probably put playlist_id of unlisted playlists
# in env variables in CircleCI.
def get_playlist(youtube, title):
    """Return users's playlist ID by title (None if not found)"""
    playlists = youtube.playlists()
    request = playlists.list(mine=True, part="id,snippet")
    current_encoding = locale.getpreferredencoding()
    
    while request:
        results = request.execute()
        for item in results["items"]:
            t = item.get("snippet", {}).get("title")
            existing_playlist_title = (t.encode(current_encoding) if hasattr(t, 'decode') else t)
            if existing_playlist_title == title:
                return item.get("id")
        request = playlists.list_next(request, results)

def create_playlist(youtube, title, privacy):
    """Create a playlist by title and return its ID"""
    debug("Creating playlist: {0}".format(title))
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
    debug("Adding video to playlist: {0}".format(playlist_id))

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
    except googleapiclient.errors.HttpError as error:
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
    playlist_id = get_playlist(youtube, title) or \
        create_playlist(youtube, title, privacy)
    if playlist_id:
        return add_video_to_existing_playlist(youtube, playlist_id, video_id)
    else:
        debug("Error adding video to playlist")
