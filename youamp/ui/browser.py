import gobject
import gtk
import pango

from youamp.ui import NOTHING_SELECTED, ARTIST_SELECTED, ALBUM_SELECTED
   
class Browser(gtk.TreeView):
    def __init__(self, config, library):
        self._model = gtk.ListStore(gobject.TYPE_STRING)
        gtk.TreeView.__init__(self, self._model)
        
        self._config = config
        
        self.set_rules_hint(True)
        self.set_headers_visible(True)
        self.set_fixed_height_mode(True)
            
        renderer = gtk.CellRendererText()
        renderer.set_property("ellipsize", pango.ELLIPSIZE_END)
        
        self.selected = NOTHING_SELECTED
        self._pos = {NOTHING_SELECTED: None, ARTIST_SELECTED: None}
        
        self._col = gtk.TreeViewColumn(None, renderer, text=0)
        self._col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        self.append_column(self._col)
        self.connect("row-activated", self._on_row_activated)
        
        self._library = library

        self.show_all()

    def _restore_pos(self):
        if self._pos[self.selected] is not None:
            gobject.idle_add(self.set_cursor, self._pos[self.selected])

    def show_albums(self, caller=None):
        if not (self.selected & ALBUM_SELECTED):
            self._config.notify("search-artist")
              
        self._col.set_title(_("Albums"))
        self.selected = ARTIST_SELECTED
        
        self._model.clear()
        self._model.append((_("All Albums"),))
        map(self._model.append, self._library.get_albums(self._config))
        self._restore_pos()

    def show_artists(self, caller=None):        
        self._col.set_title(_("Artist"))
        self.selected = NOTHING_SELECTED

        self._model.clear()
        self._model.append((_("All Artists"),))
        
        map(self._model.append, self._library.get_artists(self._config))
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

