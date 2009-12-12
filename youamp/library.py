import os
import sqlite3

from youamp import db_file
from youamp.playlist import Song, Playlist

order = dict()
order["album"] = "album ASC, tracknumber ASC"
order["date"] = "date DESC, "+order["album"]
order["playcount"] = "playcount DESC, "+order["album"]

SONG_FIELDS = "uri, title, artist, album, playcount, tracknumber, date"

class PlaylistBackend:
    def __init__(self, conn, name):
        self._conn = conn
        self.name = name
        
        if name is None:
            conn.execute("INSERT INTO playlists VALUES ('')")
            self._id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        else:
            self._id = conn.execute("SELECT rowid FROM playlists WHERE name = ?", (name,)).fetchone()[0]
    
    def rename(self, new_name):
        self._conn.execute("""
        UPDATE playlists 
        SET name = ? 
        WHERE rowid = ?""", (new_name, self._id))
        
        self._conn.commit()
      
    def get_songs(self):
        res = self._conn.execute("""
        SELECT """+SONG_FIELDS+"""
        FROM playlist_song
        JOIN songs ON song_id = songs.rowid
        WHERE pl_id = ?""", (self._id,))
        
        return [Song(e) for e in res]
    
    def update(self, songs):
        self._conn.execute("""
        DELETE FROM playlist_song
        WHERE pl_id = ?""", (self._id,))
        
        for s in songs:
            self._conn.execute("""
            INSERT INTO playlist_song 
            VALUES 
            (?, (SELECT rowid FROM songs WHERE uri = ?))""", (self._id, unicode(s.uri)))
        
        self._conn.commit()
    
    def delete(self):
        self._conn.execute("""
        DELETE FROM playlist_song
        WHERE pl_id = ?""", (self._id,))

        self._conn.execute("""
        DELETE FROM playlists
        WHERE rowid = ?""", (self._id,))
        
        self._conn.commit()

class Library:
    def __init__(self):        
        # set up connection
        self._conn = sqlite3.connect(db_file)
        self._cursor = self._conn.cursor()

    def __del__(self):
        self._conn.close()

    def get_new_playlist(self):
        return Playlist(PlaylistBackend(self._conn, None))

    def get_playlists(self):
        playlists = self._cursor.execute("SELECT name FROM playlists")
        
        lists = [Playlist(PlaylistBackend(self._conn, e[0])) for e in playlists]

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
        SELECT """+SONG_FIELDS+"""
        FROM songs 
        WHERE uri = ?""", (unicode(path),))
        
        try:
            return list(ret.next())
        except StopIteration:
            raise KeyError
    
    def get_albums(self, config):
        artist = unicode(config["search-artist"])
        where_clause = ""
        variables = (unicode(config["music-folder"]+"%"),)
        
        if artist != "":
            where_clause += " AND artist = ?"
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
        
        if config["order-by"] == "shuffle":
            order_clause = ""
        else:
            order_clause = "ORDER BY %s" % order[config["order-by"]]
        
        variables = [unicode(v) for v in variables]
                        
        playlist = self._cursor.execute("""
        SELECT """+SONG_FIELDS+"""
        FROM songs
        WHERE uri LIKE ?
        %s
        %s""" % (where_clause, order_clause), variables)
        
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
                where_clause += "AND artist || album || title LIKE ?"
                name = "%"+"%".join(name.split())+"%"  # insert wildcard on spaces
                variables += (name,)
        
        return (where_clause, variables)

    def increment_played(self, song_uri):
        self._cursor.execute("""UPDATE songs SET playcount = playcount + 1 WHERE uri = ?""", (unicode(song_uri),))
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
    
    # playlists were introdiceds in v0.6.0
    try:
        con.execute("SELECT name FROM playlists LIMIT 1")
    except sqlite3.OperationalError:
        con.execute("CREATE TABLE playlists (name TEXT)")
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
    con.execute("CREATE TABLE playlists (name TEXT)")
    con.execute("CREATE TABLE playlist_song (pl_id INT, song_id INT)")

    con.close()
