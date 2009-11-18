import gtk
import pango

from youamp.ui.browser import Browser
from youamp.ui.playlist import PlaylistLabel, SongList
from youamp.ui import ARTIST_SELECTED, ALBUM_SELECTED

class BrowseButton(gtk.Button):
    def __init__(self):
        gtk.Button.__init__(self)
        
        self.set_size_request(200, -1)
        
        self.label = gtk.Label()
        self.label.set_ellipsize(pango.ELLIPSIZE_END)
        
        self.add(self.label)
        self.unset_flags(gtk.CAN_FOCUS)
    
    def set_text(self, txt):
        self.label.set_text(txt)

class SearchView(SongList):
    SINK = SongList.SINK[0:1] # dont allow adding to library
    ORDER_MAPPING = ("album", "playcount", "date")

    def __init__(self, playlist, player, library, config, song_menu, xml):
        self.view = gtk.VBox()
        self.view.playlist = playlist
        self.view.restore = super(SearchView, self).restore
        self.view.top = self

        SongList.__init__(self, playlist, player, library, song_menu)

        self._config = config
        self._is_browser = config["is-browser"]
        
        self.label = PlaylistLabel(playlist, icon="system-file-manager")

        # Navi Controls
        self.view.set_spacing(5)

        navi = gtk.HBox()
        navi.set_spacing(5)
        navi.set_border_width(5)
        self.view.pack_start(navi, expand=False)

        hbox = gtk.HBox()
        navi.pack_start(hbox, expand=False)
        
        # Search Label
        self._search_label = gtk.Label(_("Search"))
        self._search_label.set_size_request(100, -1)
        hbox.pack_start(self._search_label, expand=False)
        
        # Browse Button
        self._browse_button = gtk.Button(_("Browse"))
        self._browse_button.connect("clicked", self._show_artists)
        self._browse_button.set_size_request(100, -1)
        hbox.pack_start(self._browse_button, expand=False)

        arrow = gtk.Button()
        arrow.set_relief(gtk.RELIEF_NONE)
        arrow.add(gtk.Arrow(gtk.ARROW_DOWN, gtk.SHADOW_IN))
        arrow.unset_flags(gtk.CAN_FOCUS)
        hbox.pack_start(arrow, expand=False)

        m = xml.get_object("view_menu")
        m.attach_to_widget(arrow, lambda *args: None)

        arrow.connect("clicked", self._view_menu_pop, m)

        # Navi Artist Button
        self._artist = BrowseButton()
        self._artist.connect("clicked", self._show_albums)
        navi.pack_start(self._artist, expand=False)
        
        # Navi Album Button
        self._album = BrowseButton()
        self._album.connect("clicked", self._select_album)
        navi.pack_start(self._album, expand=False)
        
        # Navi Search Entry
        self._search_entry = gtk.Entry()
        self._search_entry.connect("activate", self._on_search_click)
        self._search_entry.set_text(self._config["search-str"])
        navi.pack_start(self._search_entry, expand=True)
        
        # Order Combo
        order = gtk.combo_box_new_text()
        order.append_text(_("album"))
        order.append_text(_("playcount"))
        order.append_text(_("date added"))
        order.append_text(_("shuffle"))
        # disable change by scrolling -> too expensive
        order.connect("scroll-event", lambda *args: True)
        order.set_active(0)
        order.connect("changed", self._on_order_changed)
        
        navi.pack_end(order, expand=False)
        navi.pack_end(gtk.Label(_("Order:")), expand=False)
        
        #self._shndl = shuffle.connect("toggled", self._on_shuffle_toggled)
        #self._shuffle = shuffle
        
        # Scrolled View
        self._scroll = gtk.ScrolledWindow()
        self._scroll.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        self._scroll.set_shadow_type(gtk.SHADOW_IN)
        self.view.pack_start(self._scroll)
        
        self._browser = Browser(config, library)
        
        self._scroll.add(self)

        self.view.show_all()

        # browser callbacks
        self._config.notify_add("search-artist", self._on_artist_changed)
        self._config.notify_add("search-album", self._on_album_changed)
        
        self._config.notify_add("is-browser", self._on_view_changed)
        self._config.notify_add("shuffle", self._update_shuffle_btn)

    def _on_order_changed(self, caller):        
        o = caller.get_active()
        if o < 3:
            self._model.order_by(self.ORDER_MAPPING[o])
        else:
            self._model.shuffle(True)

    def _view_menu_pop(self, button, m):
        a = button.get_allocation()
        ap = button.get_parent_window().get_position()

        m.popup(None, None, lambda *arg: (a.x + ap[0], a.y + a.height + ap[1], False), 0, 0)
     
    def _update_shuffle_btn(self, client, cxn_id, entry, data):
        self._shuffle.handler_block(self._shndl)
        self._shuffle.set_active(entry.get_value().get_bool())
        self._shuffle.handler_unblock(self._shndl)
    
    def _on_view_changed(self, client, cxn_id, entry, data):
        is_browser = entry.get_value().get_bool()
        
        if is_browser:
            self.browse_mode()
            self._browser.selected = ARTIST_SELECTED | ALBUM_SELECTED
        else:
            self.search_mode()

    def browse_mode(self):
        self._search_label.hide()
        self._search_entry.hide()
        self._browse_button.show()
        
        if self._config["is-browser"]:
            self._artist.show()
            self._album.show()
        else:
            self._show_artists()

    def restore(self):
        if self._config["is-browser"]:
            a = self._config["search-artist"]
            txt = a if a != "" else _("All Artists")
            self._artist.set_text(txt)   
            
            a = self._config["search-album"]
            txt = a if a !=  "" else _("All Albums")                
            self._album.set_text(txt)

            self._browser.selected = ARTIST_SELECTED | ALBUM_SELECTED
            self._search_label.hide()
            self._search_entry.hide()
        else:
            self._browse_button.hide()
            self._artist.hide()
            self._album.hide()

        SongList.restore(self)
            
    def _on_shuffle_toggled(self, caller):
        new_shuffle_state = not self._config["shuffle"]
        self._config["shuffle"] = new_shuffle_state
        
        self._model.shuffle(new_shuffle_state)
        self.set_cursor(self._model.pos)
        
    def _browse_complete(self):        
        self._search_entry.set_text("")
        self._config["is-browser"] = True
        self._config.notify("is-browser")
                
        self._show_playlist()
 
    def _on_search_click(self, caller):
        self._config["search-str"] = caller.get_text()
        self._config["is-browser"] = False
        self._config.notify("is-browser")
   
        self._config.notify("search-str")
    
    def search_mode(self):
        self._browse_button.hide()
        self._artist.hide()
        self._album.hide()
        self._search_label.show()
        self._search_entry.show()
        
        if self._browser.get_parent() is not None:
            self._show_playlist()
    
    def _show_playlist(self):
        if self.get_parent() is None:
            self._scroll.remove(self._browser)
            self._scroll.add(self)

    def _show_browser(self):
        if self._browser.get_parent() is None:
            self._scroll.remove(self)
            self._scroll.add(self._browser)

    def _on_artist_changed(self, client, cxn_id, entry, data):
        val = entry.get_value().get_string()

        val = val if val != "" else _("All Artists")
        
        self._artist.set_text(val)
        self._artist.show()
        
        if not (self._browser.selected & ALBUM_SELECTED):
            self._album.hide()

    def _on_album_changed(self, client, cxn_id, entry, data):
        val = entry.get_value().get_string()
  
        val = val if val != "" else _("All Albums")
        
        self._album.set_text(val)
        self._album.show()
        
        self._browse_complete()

    def _select_album(self, caller):        
        if not (self._browser.selected & ALBUM_SELECTED):
            self._browser.selected |= ALBUM_SELECTED
            self._config.notify("search-album")
        
    def _show_albums(self, caller):
        self._show_browser()
        self._browser.show_albums()

    def _show_artists(self, caller=None):
        self._show_browser()
        self._browser.show_artists()

