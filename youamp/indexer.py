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

class MetadataError(Exception): pass

def get_metadata_sane(path):
    meta = get_metadata_raw(path)
    
    if meta is None:
        return None

    meta["mtime"] = os.path.getmtime(path)

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
   
    # no visible tags -> set title = filename
    if "title" not in meta and \
       "artist" not in meta and \
       "album" not in meta:
            fname = path.rindex("/")
            fnend = path.rindex(".")
            meta["title"] = path[fname+1:fnend]
            meta["artist"] = ""
            meta["album"] = ""
    else:   
        # sanitise tags
        for k in ("title", "artist", "album"):        
            meta[k] = meta[k].strip() if k in meta else ""

    # sqlite wants only unicode strings
    for k, v in meta.iteritems():
        meta[k] = unicode(v)

    return meta

def get_metadata_raw(path):
    if path.lower().endswith("mp3"):
        try:
            f = mutagen.easyid3.EasyID3(path)
        except (ID3NoHeaderError, ID3BadUnsynchData):
            sys.stderr.write("Bad ID3 Header: %s\n" % path)
            f = {}
        except IOError, e:
            raise MetadataError(str(e))
    else:
        try:
            f = mutagen.File(path)
        except:
            raise MetadataError("%s: error in Mutagen" % path)
    
    if f is None:
        raise MetadataError("%s: not a media file" % path)
    
    meta = {}
    
    for k, v in f.items():
        # FIXME what if v is not a list
        try:
            v = str(", ".join(v))   # flatten value
        except TypeError:
            raise MetadataError("%s: wrong type for %s" % (path, k))
        
        meta[k] = v
    
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
        db_files = con.execute("SELECT uri, strftime('%s', date) FROM songs").fetchall()
        to_update = []
        
        mod_count = 0

        for path, old_mtime in db_files:
            if os.path.exists(path):
                mtime = os.path.getmtime(path)
                
                if mtime - 1 > float(old_mtime): # float precision stuff
                    to_update.append(path)
                
                disc_files.remove(str(path)) # convert unicode
            else:
                con.execute("DELETE FROM songs WHERE uri = ?", (path,))
                print "Removed: %s" % path
            
        # update files
        for path in to_update: 
            try:        
                song = get_metadata_sane(path)
            except MetadataError, e:
                sys.stderr.write("Skipped "+str(e)+"\n")
                continue

            # store metadata in database (uri, title, artist, album, genre, tracknumber, playcount, date)
            con.execute("""
            UPDATE songs 
            SET title = ?, artist = ?, album = ?, tracknumber = ?, date = datetime(?, 'unixepoch')
            WHERE uri = ? """,
            (song["title"], song["artist"], song["album"], song["tracknumber"], song["mtime"], unicode(path)))

            print "Updated: %s" % path
            mod_count += 1
  
  
        # add new files
        for path in disc_files: 
            try:        
                song = get_metadata_sane(path)
            except MetadataError, e:
                sys.stderr.write("Skipped "+str(e)+"\n")
                continue

            # store metadata in database (uri, title, artist, album, genre, tracknumber, playcount, date)
            con.execute("INSERT INTO songs VALUES (?, ?, ?, ?, '', ?, 0, datetime(?, 'unixepoch'))", \
                (unicode(path), song["title"], song["artist"], song["album"], song["tracknumber"], song["mtime"]))

            print "Added: %s" % path
            mod_count += 1
        
        con.commit()
        con.close()

        self.emit("update-complete", mod_count > 0)
