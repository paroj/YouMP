from gi.repository import Gtk, Gdk, Pango

from youamp.ui.browser import Browser
from youamp.ui.playlist import SongsTab
from youamp.ui import ARTIST_SELECTED, ALBUM_SELECTED

class BrowseButton(Gtk.Button):
    def __init__(self):
        Gtk.Button.__init__(self)
        
        self.set_size_request(200, -1)
        
        self.label = Gtk.Label()
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        
        self.add(self.label)
        self.set_can_focus(False)
    
    def set_text(self, txt):
        self.label.set_text(txt)

class SearchView(SongsTab):
    def __init__(self, playlist, controller, config, song_menu, xml):
        SongsTab.__init__(self, playlist, controller, song_menu)
        
        # dont allow adding to library
        self.playlist.enable_model_drag_dest(self.playlist.SINK[0:1], Gdk.DragAction.LINK)
        
        self._config = config
        self._is_browser = config["is-browser"]
           
        # Navi Controls        
        navi = self._navi
        
        hbox = Gtk.HBox()
        navi.pack_start(hbox, False, True, 0)
        
        # Search Label
        self._search_label = Gtk.Label(label=_("Search"))
        self._search_label.set_size_request(100, -1)
        hbox.pack_start(self._search_label, False, True, 0)
        
        # Browse Button
        self._browse_button = Gtk.Button(_("Browse"))
        self._browse_button.connect("clicked", self._show_artists)
        self._browse_button.set_size_request(100, -1)
        hbox.pack_start(self._browse_button, False, True, 0)

        arrow = xml.get_object("sw_arrow")
        hbox.pack_start(arrow, False, True, 0)

        m = xml.get_object("view_menu")
        m.attach_to_widget(arrow, lambda *args: None)

        arrow.connect("clicked", self._view_menu_pop, m)

        # Navi Artist Button
        self._artist = BrowseButton()
        self._artist.connect("clicked", self._show_albums)
        navi.pack_start(self._artist, False, True, 0)
        
        # Navi Album Button
        self._album = BrowseButton()
        self._album.connect("clicked", self._select_album)
        navi.pack_start(self._album, False, True, 0)
        
        # Navi Search Entry
        self._search_entry = Gtk.Entry()
        self._search_entry.connect("activate", self._on_search_click)
        self._search_entry.set_text(self._config["search-str"])
        navi.pack_start(self._search_entry, True, True, 0)
        
        # Order ComboBox
        self.order.set_active(controller.ORDER_MAPPING.index(config["order-by"]))       
        self.order.connect("changed", controller.order_changed, playlist)
      
        self._nb = Gtk.Notebook()
        self._nb.set_show_tabs(False)
        self._nb.set_show_border(False)
        self.pack_start(self._nb, True, True, 0)
        
        # move playlist to notebook
        self._scroll.reparent(self._nb)
        
        browser_scroll = Gtk.ScrolledWindow()
        browser_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
        browser_scroll.set_shadow_type(Gtk.ShadowType.IN)
        self._nb.append_page(browser_scroll, None)
        
        self._browser = Browser(config, controller.library)
        browser_scroll.add(self._browser)

        self.show_all()

        # browser callbacks
        self._config.connect("changed::search-artist", self._on_artist_changed)
        self._config.connect("changed::search-album", self._on_album_changed)
        self._config.connect("changed::is-browser", self._on_view_changed)
        self._config.connect("changed::pos", lambda *a: self.playlist.set_cursor(self.playlist._model.pos))

    def _view_menu_pop(self, button, m):
        a = button.get_allocation()
        ap = button.get_parent_window().get_position()

        # FIXME??
        m.popup(None, None, lambda *arg: (a.x + ap[0], a.y + a.height + ap[1], False), 0, 0, Gtk.get_current_event_time())
         
    def _on_view_changed(self, client, entry):
        is_browser = client[entry]
        
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

        self.playlist.restore()
        
    def _browse_complete(self):        
        self._search_entry.set_text("")
        self._config["is-browser"] = True
                
        self._show_playlist()
 
    def _on_search_click(self, caller):
        self._config["search-str"] = caller.get_text()
        self._config["is-browser"] = False
    
    def search_mode(self):
        self._browse_button.hide()
        self._artist.hide()
        self._album.hide()
        self._search_label.show()
        self._search_entry.show()

        self._show_playlist()
    
    def _show_playlist(self):
        self._nb.set_current_page(0)

    def _show_browser(self):
        self._nb.set_current_page(1)

    def _on_artist_changed(self, client, key):
        val = client[key] if client[key] != "" else _("All Artists")
        
        self._artist.set_text(val)
        self._artist.show()
        
        if not (self._browser.selected & ALBUM_SELECTED):
            self._album.hide()

    def _on_album_changed(self, client, key):
        val = client[key] if client[key] != "" else _("All Albums")
        
        self._album.set_text(val)
        self._album.show()
        
        self._browse_complete()

    def _select_album(self, caller):        
        if not (self._browser.selected & ALBUM_SELECTED):
            self._browser.selected |= ALBUM_SELECTED
            self._config["search-album"] = self._config["search-album"]
        
    def _show_albums(self, caller):
        self._show_browser()
        self._browser.show_albums()

    def _show_artists(self, caller=None):
        self._show_browser()
        self._browser.show_artists()

