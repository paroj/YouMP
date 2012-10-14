from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from youamp.ui import NOTHING_SELECTED, ARTIST_SELECTED, ALBUM_SELECTED
   
class Browser(Gtk.TreeView):
    def __init__(self, config, library):
        self._model = Gtk.ListStore(GObject.TYPE_STRING)
        Gtk.TreeView.__init__(self, self._model)
        
        self._config = config
        
        self.set_rules_hint(True)
        self.set_headers_visible(True)
        self.set_fixed_height_mode(True)
            
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        
        self.selected = NOTHING_SELECTED
        self._pos = {NOTHING_SELECTED: None, ARTIST_SELECTED: None}
        
        self._col = Gtk.TreeViewColumn(None, renderer)
        self._col.set_cell_data_func(renderer, self._data_func)
        self._col.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self.append_column(self._col)
        self.connect("row-activated", self._on_row_activated)
        
        self._library = library

        self.show_all()

    def _data_func(self, col, renderer, model, itr, key):
        v = model[itr][0]        
        i = model.get_path(itr)[0]
        
        renderer.set_property("weight", Pango.Weight.BOLD if i == 0 else Pango.Weight.NORMAL)
        
        renderer.set_property("text", v)

    def _restore_pos(self):
        if self._pos[self.selected] is not None:
            GObject.idle_add(self.set_cursor, self._pos[self.selected])

    def show_albums(self, caller=None):
        if not (self.selected & ALBUM_SELECTED):
            self._config["search-artist"] = self._config["search-artist"] # generate "changed::"
              
        self._col.set_title(_("Albums"))
        self.selected = ARTIST_SELECTED
        
        self._model.clear()
        self._model.append((_("All Albums"),))
        list(map(self._model.append, self._library.get_albums(self._config)))
        self._restore_pos()

    def show_artists(self, caller=None):        
        self._col.set_title(_("Artist"))
        self.selected = NOTHING_SELECTED

        self._model.clear()
        self._model.append((_("All Artists"),))
        
        list(map(self._model.append, self._library.get_artists(self._config)))
        self._restore_pos()
        
        # reset pos for next step
        self._pos[ARTIST_SELECTED] = None
        
    def _on_row_activated(self, caller, path, column):           
        selected = self._model[path][0] if path[0] > 0 else ""
        self._pos[self.selected] = path[0]
      
        if not (self.selected & ARTIST_SELECTED):
            self.selected |= ARTIST_SELECTED
                 
            self._config["search-artist"] = selected
            self.show_albums()
        elif not (self.selected & ALBUM_SELECTED):
            self.selected |= ALBUM_SELECTED
            
            notify = self._config["search-album"] == selected

            self._config["search-album"] = selected
            
            if notify:
                self._config.notify("search-album")

