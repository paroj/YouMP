import fnmatch
import os

import dbus
import gobject

from youamp import Song, Playlist, playlist_dir

order = dict()
order["album"] = "album ASC, trackno ASC"
order["date"] = "mtime.MetaDataValue DESC, "+order["album"]
order["playcount"] = "playcount DESC, "+order["album"]

def save_list(list, *args):
    # call save from main loop so it happens after the drop
    gobject.idle_add(list.save)

class Library:
    def __init__(self):
        # set up connection
        session_bus = dbus.SessionBus()

        obj = session_bus.get_object("org.freedesktop.Tracker", "/org/freedesktop/Tracker/Search")
        self._search = dbus.Interface(obj, dbus_interface="org.freedesktop.Tracker.Search")

        obj = session_bus.get_object("org.freedesktop.Tracker", "/org/freedesktop/Tracker/Metadata")
        self._meta = dbus.Interface(obj, dbus_interface="org.freedesktop.Tracker.Metadata")

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
        query = """
        SELECT DISTINCT
        artist.MetadataDisplay
        FROM Services S
        JOIN ServiceMetadata artist ON S.ID = artist.ServiceID
        WHERE S.ServiceTypeID = (SELECT TypeId FROM ServiceTypes WHERE TypeName = "Music")
        AND artist.MetaDataID = (SELECT ID FROM MetaDataTypes WHERE MetaName ='Audio:Artist')
        AND S.Path LIKE "{0}%"
        ORDER BY artist.MetaDataValue ASC
        """.format(config["music-folder"])

        return self._search.SqlQuery(query)

    def get_albums(self, config):
        artist = unicode(config["search-artist"])
        if artist != "":
            where_clause = """AND artist.MetadataDisplay = "{0}" """.format(artist)
        else:
            where_clause = ""

        query = """
        SELECT DISTINCT
        album.MetadataDisplay
        FROM Services S
        JOIN ServiceMetadata album ON S.ID = album.ServiceID
        JOIN ServiceMetadata artist ON S.ID = artist.ServiceID
        WHERE S.ServiceTypeID = (SELECT TypeId FROM ServiceTypes WHERE TypeName = "Music")
        AND album.MetaDataID = (SELECT ID FROM MetaDataTypes WHERE MetaName ='Audio:Album')
        AND artist.MetaDataID = (SELECT ID FROM MetaDataTypes WHERE MetaName ='Audio:Artist')
        AND S.Path LIKE "{0}%"
        {1}
        ORDER BY artist.MetaDataValue ASC, album.MetaDataValue ASC
        """.format(config["music-folder"], where_clause)

        return self._search.SqlQuery(query)

    def get_metadata(self, path):
        ret = self._meta.Get("Music", path, ["Audio:Title", "Audio:Artist", "Audio:Album", "Audio:PlayCount", "Audio:TrackNo"])

        return ret

    def get_tracks(self, config):        
        where_clause= self._build_where_clause(config)

        query = """
        SELECT DISTINCT S.Path || "/" || S.Name,
        (SELECT MetaDataDisplay FROM ServiceMetaData WHERE S.ID = ServiceID AND MetaDataID = (SELECT ID FROM MetaDataTypes WHERE MetaName ='Audio:Title')) AS title,
        (SELECT MetaDataDisplay FROM ServiceMetaData WHERE S.ID = ServiceID AND MetaDataID = (SELECT ID FROM MetaDataTypes WHERE MetaName ='Audio:Artist')) AS artist,
        (SELECT MetaDataDisplay FROM ServiceMetaData WHERE S.ID = ServiceID AND MetaDataID = (SELECT ID FROM MetaDataTypes WHERE MetaName ='Audio:Album')) AS album,
        (SELECT MetaDataValue FROM ServiceNumericMetaData WHERE S.ID = ServiceID AND MetaDataID = (SELECT ID FROM MetaDataTypes WHERE MetaName ='Audio:PlayCount')) AS playcount,
        (SELECT MetaDataValue FROM ServiceNumericMetaData WHERE S.ID = ServiceID AND MetaDataID = (SELECT ID FROM MetaDataTypes WHERE MetaName ='Audio:TrackNo')) AS trackno
        FROM Services S
        JOIN ServiceNumericMetaData mtime ON S.ID = mtime.ServiceID
        JOIN ServiceMetadata title ON S.ID = title.ServiceID
        JOIN ServiceMetadata artist ON S.ID = artist.ServiceID
        WHERE S.ServiceTypeID = (SELECT TypeId FROM ServiceTypes WHERE TypeName = "Music")
        AND mtime.MetaDataID = (SELECT ID FROM MetaDataTypes WHERE MetaName ='File:Modified')
        AND title.MetaDataID = (SELECT ID FROM MetaDataTypes WHERE MetaName ='Audio:Title')
        AND artist.MetaDataID = (SELECT ID FROM MetaDataTypes WHERE MetaName ='Audio:Artist')
        AND S.Path LIKE "{0}%"
        {1}
        ORDER BY {2};
        """.format(config["music-folder"], where_clause, order[config["order-by"]])

        try:
            return [Song(s) for s in self._search.SqlQuery(query)]
        except Exception as e:
            print e
            return []
    
    def _build_where_clause(self, config):
        where_clause = ""
        
        if config["is-browser"]:
            artist = unicode(config["search-artist"])
            album = unicode(config["search-album"])
            
            if (artist != "" or album != ""):
                where_clause = "AND "
            
            # build query
            if artist != "":
                where_clause += "artist.MetadataDisplay = '{0}'".format(artist)
            
            if artist != "" and album != "":
                where_clause += " AND "
            
            if album != "":
                where_clause += "album = '{0}'".format(album)
        else:
            name = unicode(config["search-str"])
            
            if name != "":
                name = "%"+"%".join(name.split())+"%"  # insert wildcard on spaces

                where_clause = """
                AND artist.MetadataDisplay || album || title.MetadataDisplay
                LIKE "{0}"
                """.format(name)
        
        return where_clause

    def increment_played(self, song_uri):
        cnt = self._meta.Get("Music", song_uri, ["Audio:PlayCount"])[0]

        cnt = int(cnt) if cnt != "" else 0
            
        self._meta.Set("Music", song_uri, ["Audio:PlayCount"], [str(cnt+1)])

