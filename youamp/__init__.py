import os
import os.path
import fnmatch
import gtk
import random
import hashlib
import gtk.gdk
import gobject
from gobject import GObject

from mutagen.id3 import ID3, ID3NoHeaderError

from xdg.BaseDirectory import xdg_cache_home, xdg_data_home

VERSION = "0.6.0"

IS_MAEMO = False

# device specific settings
MAX_VOL = 2.0

data_path = "data/"
if not os.path.exists(data_path):
    data_path = "/usr/share/youamp/"

media_art = xdg_cache_home+"/media-art/"
playlist_dir = xdg_cache_home+"/youamp/"
db_file = xdg_data_home+"/youamp/musicdb"

try:
    os.makedirs(playlist_dir)
except OSError:
    # dir already exists
    pass

class PlaylistMux(GObject):
    __gsignals__ = {"list-switched": (gobject.SIGNAL_RUN_LAST, None, (object,))}

    def __init__(self, cur):
        GObject.__init__(self)
        
        self.current = cur
        self.jump_to = None

    def jump_index(self):
        if self.current is not self.jump_to[0]:
            self.current = self.jump_to[0]
            self.emit("list-switched", self.current)

        return self.index(self.jump_to[1])
    
    def next_song(self, song):
        return self.current.next_song(song)
    
    def index(self, v):
        return self.current.index(v)

    @property
    def pos(self):
        return self.current.pos

    @pos.setter
    def pos(self, val):
        self.current.pos = val

    def __eq__(self, other):
        return self.current is other

    def set(self, pl):
        self.current = pl

    def get(self):
        return self.current

    def __getitem__(self, k):
        return self.current[k]

    def __setitem__(self, k, v):
        self.current[k] = v

    def __len__(self):
        return len(self.current)

    def shuffle(self, shuffle):
        self.current.shuffle(shuffle)

    def update(self, new_list):
        self.current.update(new_list)

class Playlist(gtk.ListStore):    
    def __init__(self, title=None):
        gtk.ListStore.__init__(self, object)

        self.pos = 0
        self.title = title
        self.path = playlist_dir+"{0}.m3u"

        # shuffled positions
        self._permutation = None

    def next_song(self, song):
        # nothing changed, just give next
        if self[self.pos] is song:
            return self.pos + 1
        
        # we were just switched to so play the selected song
        return self.pos

    def order_by(self, order):
        l = range(0, len(self))

        if order == "album":
            l.sort(self._sort_album)
        else:
            l.sort(self._sort_playcount)

        self.reorder(l)

    def update(self, playlist):
        self.clear()

        for s in playlist:
            self.append((s,))
    
    def shuffle(self, shuffle):
        """shuffle/ unshuffle the playlist"""
        if shuffle:
            # build permutation
            self._permutation = range(0, len(self))
            random.shuffle(self._permutation)
        else:
            # build permutation inverse
            inv_perm = range(0, len(self))
            for i in xrange(0, len(self)):
                inv_perm[self._permutation[i]] = i
            
            self._permutation = inv_perm
            
        self.reorder(self._permutation)
        
        # update current position
        try:
            self.pos = self._permutation.index(self.pos)
        except ValueError:
            # new playlist was set shuffled
            self.pos = 0

    def _sort_playcount(self, i1, i2):
        s1 = self[i1]
        s2 = self[i2]

        return -cmp(s1["playcount"], s2["playcount"])

    def _sort_album(self, i1, i2):
        s1 = self[i1]
        s2 = self[i2]

        # sort by album and then by trackno
        score = cmp(s1["album"], s2["album"])
        
        if score == 0:
            score = cmp(s1["trackno"], s2["trackno"])

        return score

    def rename(self, new_title):
        path = (playlist_dir+"{0}.m3u").format(self.title)
        new_path = (playlist_dir+"{0}.m3u").format(new_title)
        os.rename(path, new_path)
        self.title = new_title

    def delete(self):
        path = (playlist_dir+"{0}.m3u").format(self.title)
        os.remove(path)

    def load(self, library):
        path = self.path.format(self.title)
        
        for loc in file(path).read().splitlines():
            # FIXME only for transition
            if loc == "#EXTM3U":
                continue
            
            try:
                m = library.get_metadata(loc)
                self.append((Song([loc]+m),))  
            except KeyError:
                pass
            
    def save(self):
        path = self.path.format(self.title)
        f = file(path, "w")
    
        for e in self:
            f.write(e[0].uri+"\n")
        
        f.close()

    def __getitem__(self, k):
        return gtk.ListStore.__getitem__(self, k)[0]
    
    def __setitem__(self, k, v):
        gtk.ListStore.__getitem__(self, k)[0] = v
    
    def next(self, v):
        return self.index(v) + 1
    
    def index(self, v):
        for i in xrange(len(self)):
            if self[i] is v:
                return i
        
        return None

class Song(dict):
    def __init__(self, data):
        dict.__init__(self)
                
        if not isinstance(data, str):
            self.uri = data[0]
            self["title"] = data[1]
            self["artist"] = data[2]
            self["album"] = data[3] if data[3] != "" else _("None")
            self["playcount"] = int(data[4]) if data[4] != "" else 0
            self["trackno"] = int(data[5]) if data[5] != "" else 0
        else:
            self.uri = data
    
    def cover_uri(self):        
        dir = os.path.dirname(self.uri)
        
        try:
            img = fnmatch.filter(os.listdir(dir), "*.jpg")[0]
        except IndexError:
            return None
        
        return os.path.join(dir, img)

    def cover_image(self, size):
        path = self.cover_uri()

        if path is None:
            # no image in song directory
            # try to load from ID3
            try:
                id3 = ID3(self.uri)
                if len(id3.getall('APIC')) > 0:
                    apic = id3.getall('APIC')[0]
                    loader = gtk.gdk.PixbufLoader()
                    loader.set_size(*size)
                    loader.write(apic.data)
                    loader.close()
                    return loader.get_pixbuf()
            except ID3NoHeaderError:
                pass

            return None
        else:
            # use the image in song directory
            return gtk.gdk.pixbuf_new_from_file_at_size(path, *size)

    def cover_image_tracker(self, size):
        # use the image in song directory
        path = self.cover_uri()

        if path is None:
            # no image in song directory
            # try to look in cache
            artist = self["artist"].strip().lower()
            album = self["album"].strip().lower()
            album = hashlib.md5(album).hexdigest()
            artist = hashlib.md5(artist).hexdigest()

            path = media_art+"album-{0}-{1}.jpeg".format(artist, album)
            
            if not os.path.exists(path):
                return None

        return gtk.gdk.pixbuf_new_from_file_at_size(path, *size)

