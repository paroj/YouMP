import sqlite3

from gi.repository import GObject, Gdk, GdkPixbuf

import os
import sys
import thread

import hashlib
import unicodedata

import tagpy

from youamp import db_file, media_art, KNOWN_EXTS


def get_metadata_sane(path):
    meta = get_metadata_raw(path)
    
    if meta is None:
        return None

    meta["mtime"] = os.path.getmtime(path)

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

    return meta

def get_metadata_raw(path):
    f = tagpy.FileRef(path)
    t = f.tag()
    
    return {"title": t.title, "artist": t.artist, "album": t.album, "tracknumber": t.track}

def media_art_identifier(meta):
    """calculate media art identifier as in bgo #520516. (the same as banshee)"""
    hashstr = "%s\t%s" % (meta["artist"], meta["album"])
    hashstr = unicodedata.normalize("NFKD", hashstr)
    hash = hashlib.md5(hashstr).hexdigest()
    
    return media_art+"album-%s.jpeg" % hash
        
def extract_cover(path, meta):
    try:
        id3 = ID3(path)
        if len(id3.getall('APIC')) > 0:
            apic = id3.getall('APIC')[0]
            loader = GdkPixbuf.PixbufLoader()
            loader.write(apic.data)
            loader.close()
            pb = loader.get_pixbuf()
            pb.save(media_art_identifier(meta), "jpeg")
    except:
        pass

class Indexer(GObject.GObject):
    __gsignals__ = {"update-complete": (GObject.SignalFlags.RUN_LAST, None, (bool,))}
        
    def __init__(self):
        GObject.GObject.__init__(self)

    # start update thread
    def update(self, folders):
        thread.start_new_thread(self._update, (folders,))

    def _get_files(self, folders):
        filelist = []
        
        for folder in folders:
            for root, dirs, files in os.walk(folder):
                if "/." in root:
                    continue # hidden directory
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
            if os.path.exists(path) and "/." not in path: # FIXME transition fix
                mtime = os.path.getmtime(path)
                
                if mtime - 1 > float(old_mtime): # float precision stuff
                    to_update.append(path)

                disc_files.remove(path.encode("utf-8")) # convert unicode
            else:
                con.execute("DELETE FROM songs WHERE uri = ?", (path,))
                print "Removed: %s" % path
            
        # update files
        for path in to_update: 
            try:        
                song = get_metadata_sane(path)
            except ValueErrir as e:
                sys.stderr.write("Skipped "+path+"\n")
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
            except ValueError as e:
                sys.stderr.write("Skipped "+path+"\n")
                continue

            # store metadata in database (uri, title, artist, album, genre, tracknumber, playcount, date)
            con.execute("INSERT INTO songs VALUES (?, ?, ?, ?, '', ?, 0, datetime(?, 'unixepoch'))", \
                (path.decode("utf-8"), song["title"], song["artist"], song["album"], song["tracknumber"], song["mtime"]))

            print "Added: %s" % path
            mod_count += 1
        
        con.commit()
        con.close()

        self.emit("update-complete", mod_count > 0)
