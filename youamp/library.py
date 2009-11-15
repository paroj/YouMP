import os
import sqlite3
import fnmatch
import gobject

from youamp import Song, Playlist, db_file, playlist_dir

order = dict()
order["album"] = "album ASC, tracknumber ASC"
order["date"] = "date DESC, "+order["album"]
order["playcount"] = "playcount DESC, "+order["album"]

def save_list(list, *args):
    # call save from main loop so it happens after the drop
    gobject.idle_add(list.save)

class Library:
    def __init__(self):        
        # set up connection
        self._conn = sqlite3.connect(db_file)
        self._cursor = self._conn.cursor()

    def __del__(self):
        self.join()
        self._conn.close()

    def get_new_playlist(self):
        l = Playlist()
        l.connect("row-inserted", save_list)
        l.connect("row-deleted", save_list)
        return l

    def get_playlists(self):
        lists = fnmatch.filter(os.listdir(playlist_dir), "*.m3u")
        lists = [fn[:fn.rindex(".")] for fn in lists]
        lists = [Playlist(title=t) for t in lists]
        [l.load(self) for l in lists]

        [l.connect("row-inserted", save_list) for l in lists]
        [l.connect("row-deleted", save_list) for l in lists]

        return lists

    def get_artists(self, config):
        artists = self._cursor.execute("""
        SELECT DISTINCT artist 
        FROM songs
        WHERE uri LIKE ?
        ORDER BY artist ASC""", (unicode(config["music-folder"]+"%"),))
        
        return artists
    
    def get_metadata(self, path):
        ret = self._cursor.execute("""
        SELECT title, artist, album, playcount, tracknumber
        FROM songs 
        WHERE uri = ?""", (unicode(path),))

        return list(ret.next())
    
    def get_albums(self, config):
        artist = unicode(config["search-artist"])
        where_clause = ""
        variables = (unicode(config["music-folder"]+"%"),)
        
        if artist != "":
            where_clause += "WHERE artist = ?"
            variables += (artist,)

        albums = self._cursor.execute("""
        SELECT DISTINCT album
        FROM songs
        WHERE uri LIKE ?
        %s
        ORDER BY artist ASC, album ASC""" % where_clause, variables)
        
        return albums
    
    def get_tracks(self, config):        
        where_clause, variables = self._build_where_clause(config)

        variables = [unicode(v) for v in variables]

        playlist = self._cursor.execute("""
        SELECT uri, title, artist, album, playcount, tracknumber
        FROM songs
        WHERE
        uri LIKE ?
        %s
        ORDER BY %s""" % (where_clause, order[config["order-by"]]), variables)
        
        for s in playlist:
            yield Song(s)
    
    def _build_where_clause(self, config):
        where_clause = ""
        variables = (config["music-folder"]+"%",)
        
        if config["is-browser"]:
            artist = config["search-artist"]
            album = config["search-album"]
            
            if (artist != "" or album != ""):
                where_clause = " AND "
            
            # build query
            if artist != "":
                where_clause += "artist = ?"
                variables += (artist,)
            
            if artist != "" and album != "":
                where_clause += " AND "
            
            if album != "":
                where_clause += "album = ?"
                variables += (album,) 
        else:
            name = config["search-str"]
            
            if name != "":
                where_clause += "WHERE artist || album || title LIKE ?"
                name = "%"+"%".join(name.split())+"%"  # insert wildcard on spaces
                variables = (name,)
        
        return (where_clause, variables)

    def increment_played(self, song_uri):
        self._cursor.execute("""UPDATE songs SET playcount = playcount + 1 WHERE uri = ?""", (song_uri,))
        self._conn.commit()

def check_db():
    if not os.path.exists(db_file):
        setup_db()
    
    con = sqlite3.connect(db_file)
  
    # the playcount column was introduced in v0.3.5
    try:
        con.execute("SELECT playcount FROM songs LIMIT 1")
    except sqlite3.OperationalError:
        con.execute("ALTER TABLE songs ADD COLUMN playcount INT")
    
    if False:
        # playlists were introdiceds in v0.6.0
        try:
            con.execute("SELECT name FROM playlist LIMIT 1")
        except sqlite3.OperationalError:
            con.execute("CREATE TABLE playlist (name TEXT)")
            con.execute("CREATE TABLE playlist_song (pl_id INT, song_id INT)")

    con.close()

def setup_db():
    try:
        os.makedirs(os.path.dirname(db_file))
    except OSError:
        # dir already exists
        pass
        
    con = sqlite3.connect(db_file)

    con.execute("CREATE TABLE songs (uri TEXT, title TEXT, artist TEXT, album TEXT, genre TEXT, tracknumber INT, playcount INT, date TEXT)")
    #con.execute("CREATE TABLE playlist (name TEXT)")
    #con.execute("CREATE TABLE playlist_song (pl_id INT, song_id INT)")

    con.close()
