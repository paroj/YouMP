import random
import functools

from gi.repository import GObject, Gtk

class PlaylistMux(GObject.GObject):
    __gsignals__ = {"list-switched": (GObject.SignalFlags.RUN_LAST, None, (object,))}

    def __init__(self, cur):
        GObject.GObject.__init__(self)
        
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
    
    def order_by(self, k):
        self.current.order_by(k)
    
    def getpos(self):
        return self.current.pos

    def setpos(self, val):
        self.current.pos = val
    
    pos = property(getpos, setpos)
    
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

class Playlist(Gtk.ListStore):    
    def __init__(self, backend):
        Gtk.ListStore.__init__(self, object)

        self.pos = 0
        self.backend = backend
        self.title = None
        self.nosync = False
        
        if backend is not None:
            self.title = backend.name
            
            for elt in self.backend.get_songs():
                Gtk.ListStore.append(self, (elt,))

            self.connect("row-inserted", self._sync)
            self.connect("row-deleted", self._sync)
    
    def _sync(self, model, *args):
        if model.nosync or self.backend is None:
            return
        
        # use idle add to make sure song was added
        GObject.idle_add(self._perform_sync)
        
    def _perform_sync(self):
        self.backend.update([e[0] for e in self])
    
    def next_song(self, song):
        # nothing changed, just give next
        if self[self.pos] is song:
            return self.pos + 1
        
        # we were just switched to so play the selected song
        return self.pos

    def order_by(self, order):
        l = list(range(0, len(self))) # new order

        if order == "album":
            l.sort(key=self._sort_album)
        elif order == "date":
            l.sort(key=self._sort_date)
        elif order == "shuffle":
            random.shuffle(l)
        else:
            l.sort(key=self._sort_playcount)

        self.reorder(l)
        self._sync(self)

        # update current position
        try:
            self.pos = l.index(self.pos)
        except ValueError:
            # new playlist was set shuffled
            self.pos = 0

    def update(self, playlist):
        self.clear()
        self.append([s for s in playlist])

    def _sort_playcount(self, i1):
        s1 = self[i1]
        return str(1/s1["playcount"])+self._sort_album(i1)
  
    def _sort_album(self, i1):
        s1 = self[i1]
        return s1["album"]+str(s1["trackno"])
    
    def _sort_date(self, i1):
        s1 = self[i1]
        
        return s1["mtime"]+self._sort_album(i1)
    
    def rename(self, new_title):
        self.backend.rename(new_title)
        self.title = new_title

    def delete(self):
        self.backend.delete()

    def __getitem__(self, k):
        return Gtk.ListStore.__getitem__(self, k)[0]
    
    def __setitem__(self, k, v):
        Gtk.ListStore.__getitem__(self, k)[0] = v
    
    def next(self, v):
        return self.index(v) + 1
    
    def insert_before(self, itr, data):
        if isinstance(data, list):
            self.nosync = True
            
            for d in data:
                Gtk.ListStore.insert_before(self, itr, (d,))
                
            self.nosync = False
            self._sync(self)
        else:
            Gtk.ListStore.insert_before(self, itr, data)
    
    def insert_after(self, itr, data):
        if isinstance(data, list):
            self.nosync = True
            
            for d in data:
                Gtk.ListStore.insert_after(self, itr, (d,))
                
            self.nosync = False
            self._sync(self)
        else:
            Gtk.ListStore.insert_after(self, itr, data)
    
    def append(self, elts):
        if isinstance(elts, list):
            self.nosync = True
                        
            for elt in elts:
                Gtk.ListStore.append(self, (elt,))
            
            self.nosync = False
            self._sync(self)
        else:
            Gtk.ListStore.append(self, (elts,))
    
    def remove(self, paths):
        if isinstance(paths, list):
            self.nosync = True
            
            for path in paths:
                Gtk.ListStore.remove(self, path)
                
            self.nosync = False
            self._sync(self)
        else:
            Gtk.ListStore.remove(self, paths)
    
    def index(self, v):
        for i in range(len(self)):
            if self[i] is v:
                return i
        
        return None

class Song(dict):
    def __init__(self, data):
        dict.__init__(self)
                
        self.uri = data[0]
        self["title"] = data[1] if data[1] != "" else _("None")
        self["artist"] = data[2] if data[2] != "" else _("None")
        self["album"] = data[3] if data[3] != "" else _("None")
        self["playcount"] = int(data[4]) if data[4] != "" else 0
        self["trackno"] = int(data[5]) if data[5] != "" else 0
        self["mtime"] = data[6]
        
        # do not try display cover if tags are insufficient
        self.display_cover = data[1] != "" and data[2] != ""
