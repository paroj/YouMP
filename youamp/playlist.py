import random

import gobject
import gtk

class PlaylistMux(gobject.GObject):
    __gsignals__ = {"list-switched": (gobject.SIGNAL_RUN_LAST, None, (object,))}

    def __init__(self, cur):
        gobject.GObject.__init__(self)
        
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

class Playlist(gtk.ListStore):    
    def __init__(self, backend):
        gtk.ListStore.__init__(self, object)

        self.pos = 0
        self.backend = backend
        self.title = None
        self.nosync = False
        
        if backend is not None:
            self.title = backend.name
            
            for elt in self.backend.get_songs():
                gtk.ListStore.append(self, (elt,))

            self.connect("row-inserted", self._sync)
            self.connect("row-deleted", self._sync)
    
    def _sync(self, model, *args):
        if model.nosync or self.backend is None:
            return
        
        # use idle add to make sure song was added
        gobject.idle_add(self._perform_sync)
        
    def _perform_sync(self):
        self.backend.update([e[0] for e in self])
    
    def next_song(self, song):
        # nothing changed, just give next
        if self[self.pos] is song:
            return self.pos + 1
        
        # we were just switched to so play the selected song
        return self.pos

    def order_by(self, order):
        l = range(0, len(self)) # new order

        if order == "album":
            l.sort(self._sort_album)
        elif order == "date":
            l.sort(self._sort_date)
        elif order == "shuffle":
            random.shuffle(l)
        else:
            l.sort(self._sort_playcount)

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

    def _sort_playcount(self, i1, i2):
        s1 = self[i1]
        s2 = self[i2]

        score = -cmp(s1["playcount"], s2["playcount"])

        if score == 0:
            score = self._sort_album(i1, i2)
        
        return score
  
    def _sort_album(self, i1, i2):
        s1 = self[i1]
        s2 = self[i2]

        # sort by album and then by trackno
        score = cmp(s1["album"], s2["album"])
        
        if score == 0:
            score = cmp(s1["trackno"], s2["trackno"])

        return score
    
    def _sort_date(self, i1, i2):
        s1 = self[i1]
        s2 = self[i2]
        
        score = -cmp(s1["mtime"], s2["mtime"])
        
        if score == 0:
            score = self._sort_album(i1, i2)
        
        return score
    
    def rename(self, new_title):
        self.backend.rename(new_title)
        self.title = new_title

    def delete(self):
        self.backend.delete()

    def __getitem__(self, k):
        return gtk.ListStore.__getitem__(self, k)[0]
    
    def __setitem__(self, k, v):
        gtk.ListStore.__getitem__(self, k)[0] = v
    
    def next(self, v):
        return self.index(v) + 1
    
    def insert_before(self, itr, data):
        if isinstance(data, list):
            self.nosync = True
            
            for d in data:
                gtk.ListStore.insert_before(self, itr, (d,))
                
            self.nosync = False
            self._sync(self)
        else:
            gtk.ListStore.insert_before(self, itr, data)
    
    def insert_after(self, itr, data):
        if isinstance(data, list):
            self.nosync = True
            
            for d in data:
                gtk.ListStore.insert_after(self, itr, (d,))
                
            self.nosync = False
            self._sync(self)
        else:
            gtk.ListStore.insert_after(self, itr, data)
    
    def append(self, elts):
        if isinstance(elts, list):
            self.nosync = True
                        
            for elt in elts:
                gtk.ListStore.append(self, (elt,))
            
            self.nosync = False
            self._sync(self)
        else:
            gtk.ListStore.append(self, (elts,))
    
    def remove(self, paths):
        if isinstance(paths, list):
            self.nosync = True
            
            for path in paths:
                gtk.ListStore.remove(self, path)
                
            self.nosync = False
            self._sync(self)
        else:
            gtk.ListStore.remove(self, paths)
    
    def index(self, v):
        for i in xrange(len(self)):
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
