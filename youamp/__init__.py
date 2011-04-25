import os
import os.path

from xdg.BaseDirectory import xdg_cache_home, xdg_data_home

VERSION = "0.6.0"

IS_MAEMO = False

# device specific settings
MAX_VOL = 2.0
KNOWN_EXTS = ("mp3", "ogg", "oga", "mp4", "m4a", "wma", "wav", "flac")

data_path = "data/"
if not os.path.exists(data_path):
    data_path = "/usr/share/youamp/"

# use high res dir
media_art = xdg_cache_home+"/media-art/300/"
db_file = xdg_data_home+"/youamp/musicdb"

try:
    os.makedirs(media_art)
except OSError:
    # dir already exists
    pass
