import os

USER_TYPES = {
        'basic': 1,
        'pro': 2,
        'corp': 3,
        }

VIDEO_CATEGORY_IDS = {
    'Film & Animation': 1,
    'Autos & Vehicles': 2,
    'Music': 10,
    'Pets & Animals': 15,
    'Sports': 17,
    'Short Movies': 18,
    'Travel & Events': 19,
    'Gaming': 20,
    'Videoblogging': 21,
    'People & Blogs': 22,
    'Comedy': 34,
    'Entertainment': 24,
    'News & Politics': 25,
    'Howto & Style': 26,
    'Education': 27,
    'Science & Technology': 28,
    'Nonprofits & Activism': 29,
    'Movies': 30,
    'Anime/Animation': 31,
    'Action/Adventure': 32,
    'Classics': 33,
    'Documentary': 35,
    'Drama': 36,
    'Family': 37,
    'Foreign': 38,
    'Horror': 39,
    'Sci-Fi/Fantasy': 40,
    'Thriller': 41,
    'Shorts': 42,
    'Shows': 43,
    'Trailers': 44,
}

# 'Uploads from Zoom' is an unlisted playlist, 
# so it's ID is stored in an environment variable.
PLAYLIST_IDS = {
    'Data Together': 'PLtsP3g9LafVul1gCctMYGm9sz5FUWr5bu',
    'Website Monitoring': 'PLtsP3g9LafVtj6IOMk05aOh-DdpuqWhue',
    'Community Calls': 'PLtsP3g9LafVsaa18lQaPXzxJU7wIcPB1O',
    'Uploads from Zoom': os.environ['DEFAULT_YOUTUBE_PLAYLIST']
}