NOTHING_SELECTED = 0
ARTIST_SELECTED = 2
ALBUM_SELECTED = 4

import gobject

def xml_escape(text):
    "escape the xml escape char"
    return gobject.markup_escape_text(text)
