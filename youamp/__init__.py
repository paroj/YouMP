import os
import os.path

from gi.repository import GLib

VERSION = "12.10"

IS_MAEMO = False

# device specific settings
MAX_VOL = 2.0
KNOWN_EXTS = ("mp3", "ogg", "oga", "mp4", "m4a", "wma", "wav", "flac")

GETTEXT_DOMAIN = "youamp"

DATA_DIR = "data/"
if not os.path.exists(DATA_DIR):
    DATA_DIR = "/opt/extras.ubuntu.com/youamp/"

# use high res dir
media_art = GLib.get_user_cache_dir()+"/media-art/300/"
db_file = GLib.get_user_data_dir()+"/youamp/musicdb"

try:
    os.makedirs(media_art)
except OSError:
    # dir already exists
    pass
