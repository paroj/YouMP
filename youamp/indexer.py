import sqlite3
import gst
import gobject
import os
import sys
import thread
import gtk.gdk
import hashlib

import mutagen
import mutagen.easyid3

from gobject import GObject
from youamp import db_file, media_art, KNOWN_EXTS
from mutagen.id3 import ID3, ID3NoHeaderError, ID3BadUnsynchData

def sanitize_metadata(path, meta):
    # no visible tags -> set title = filename
    if "title" not in meta and \
       "artist" not in meta and \
       "album" not in meta:
            fname = path.rindex("/")
            fnend = path.rindex(".")
            return {"title": path[fname+1:fnend], "artist": "", "album": "", "tracknumber": 0}
    
    if "tracknumber" in meta:
        v = meta["tracknumber"]
        
        try:
            slash = v.index("/")
            v = v[0:slash]
        except ValueError:
            pass
        
        try:
            v = int(v)
        except ValueError:
            v = 0
    else:
        v = 0
    
    meta["tracknumber"] = v
    
    # sanitise tags
    for k in ("title", "artist", "album"):        
        meta[k] = meta[k].strip() if k in meta else ""
    
    return meta

def media_art_identifier(meta):
    artist = meta["artist"].lower()
    album = meta["album"].lower()
    album = hashlib.md5(album).hexdigest()
    artist = hashlib.md5(artist).hexdigest()
    
    return media_art+"album-%s-%s.jpeg" % (artist, album)
        
def extract_cover(path, meta):
    try:
        id3 = ID3(path)
        if len(id3.getall('APIC')) > 0:
            apic = id3.getall('APIC')[0]
            loader = gtk.gdk.PixbufLoader()
            loader.write(apic.data)
            loader.close()
            pb = loader.get_pixbuf()
            pb.save(media_art_identifier(meta), "jpeg")
    except:
        pass

class Indexer(GObject):
    __gsignals__ = {"update-complete": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (bool,))}
        
    def __init__(self):
        GObject.__init__(self)

    # start update thread
    def update(self, folders):
        thread.start_new_thread(self._update, (folders,))

    def _get_files(self, folders):
        filelist = []
        
        for folder in folders:
            for root, dirs, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith(KNOWN_EXTS):
                        path = os.path.join(root, f)
                        filelist.append(path)

        return filelist

    def _update(self, folder):
        # local connection, so we can run as thread
        con = sqlite3.connect(db_file)

        disc_files = self._get_files(folder)
        db_files = con.execute("SELECT uri FROM songs").fetchall()
        
        add_count = 0

        for path, in db_files:
            try:
                disc_files.remove(str(path)) # convert unicode
            except ValueError:
                con.execute("DELETE FROM songs WHERE uri = ?", (path,))
                print "Removed: %s" % path

        # add new files
        for path in disc_files:
            if path.lower().endswith("mp3"):
                try:
                    f = mutagen.easyid3.EasyID3(path)
                except (ID3NoHeaderError, ID3BadUnsynchData):
                    sys.stderr.write("Bad ID3 Header: %s\n" % path)
                    f = {}
                except IOError, e:
                    sys.stderr.write(str(e)+"\n")
                    continue
            else:
                try:
                    f = mutagen.File(path)
                except:
                    sys.stderr.write("Skipped %s, error in Mutagen\n" % path)
                    continue

            if f is None:
                sys.stderr.write("Not a media file, skipping: %s\n" % path)
                continue
            
            song = {}
            
            for k, v in f.items():
                # FIXME what if v is not a list
                try:
                    v = str(", ".join(v))   # flatten value
                except TypeError:
                    sys.stderr.write("wrong type for %s in %s\n" % (k, path))
                    continue
                
                song[k] = v
            
            song = sanitize_metadata(path, song)
            extract_cover(path, song)

            mtime = os.path.getmtime(path)

            # sqlite wants only unicode strings
            for k, v in song.iteritems():
                song[k] = unicode(v)

            # store metadata in database (uri, title, artist, album, genre, tracknumber, playcount, date)
            con.execute("INSERT INTO songs VALUES (?, ?, ?, ?, '', ?, 0, datetime(?, 'unixepoch'))", \
                (unicode(path), song["title"], song["artist"], song["album"], song["tracknumber"], mtime))

            print "Added: %s" % path
            add_count += 1
        
        con.commit()
        con.close()

        self.emit("update-complete", add_count > 0)
