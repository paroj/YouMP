import gtk
import pynotify
import gtk.gdk

from youamp.ui.window import Window
from youamp.ui.preferences import Preferences
from youamp.ui.searchview import SearchView

from youamp.ui.playlist import PlaylistView
from youamp.ui.popupmenu import SongMenu, PlaylistMenu

from youamp.ui.elements import Controls, Icon
from youamp.ui import xml_escape

from youamp import VERSION, data_path

class UserInterface:
    NOTIFY_STR = "{0} <i>{1}</i>\n{2} <i>{3}</i>"

    def __init__(self, controller):
        player = controller.player
        config = controller.config
        library = controller.library
        scrobbler = controller.scrobbler
        
        self._controller = controller
        
        # Build Interface
        xml = gtk.Builder()
        xml.set_translation_domain("youamp")
        xml.add_from_file(data_path + "interface.ui")

        # Create Views
        self.smenu = SongMenu(config, player, xml)
        self.plmenu = PlaylistMenu(xml)
        
        sw = SearchView(controller.main_list, controller, config, self.smenu, xml)
        # restore
        sw.order.set_active(controller.ORDER_MAPPING.index(config["order-by"]))
        # signal
        sw.order.connect("changed", controller.order_changed, sw.playlist.get_model())

        self._view = [sw]
        self._cur_view = sw
         
        lists = [PlaylistView(l, controller, self.smenu, self.plmenu) for l in library.get_playlists()]
        self._view += lists
        
        # Windows
        self.window = Window(player, xml)
        about = xml.get_object("about")
        about.set_version(VERSION)

        prefs = Preferences(config, scrobbler, xml)

        # Controls
        Controls(player, config, xml)

        # Menu
        if config["is-browser"]:
            xml.get_object("view_browse").set_active(True)
        else:
            xml.get_object("view_search").set_active(True)

        # Tray Icon
        Icon(player, xml)
               
        # Notification
        pynotify.init("YouAmp")
        self._notify = pynotify.Notification(" ")
        self._notify.attach_to_status_icon(xml.get_object("statusicon1"))
        self._notify.set_urgency(pynotify.URGENCY_LOW)

        # Add {Search, Playlist}Views
        self.nb = xml.get_object("notebook1")
        
        for v in self._view:
            self.nb.append_page(v, v.label)
        
        for lv in lists:
            self.nb.set_tab_reorderable(lv, True)

        # disable implicit playlist change
        self.nb.connect("switch-page", self._change_playlist, player)
        self.nb.connect("page-reordered", self._move_lib_first)

        # Signals
        xml.connect_signals({"show-preferences": lambda *args: prefs.cshow(),
                             "show-about": lambda *args: about.show(),
                             "quit": controller.quit,
                             "key-press": self._handle_keypress,
                             "hide-on-delete": gtk.Widget.hide_on_delete,
                             "toggle": lambda caller: player.toggle(),
                             "previous": lambda caller: player.previous(),
                             "next": lambda caller: player.next(),
                             "seek-change": lambda caller, *a: player.seek_to(caller.get_value()),
                             "view-search": lambda caller: self._cur_view.search_mode(),
                             "view-browse": lambda caller: self._cur_view.browse_mode(),
                             "select-current": lambda caller: self._cur_view.playlist.select_current(),
                             "new-playlist": lambda caller: self.add_playlist(library.get_new_playlist())})

        self._toggle = xml.get_object("playback_item")
        self._thndl = self._toggle.connect("toggled", lambda caller: player.toggle())
        
        player.connect("toggled", self._watch_toggled)
        player.connect("song-changed", self._update_pos)
        player.playlist.connect("list-switched", self._switch_to)
        
        # change to library on browsing
        config.notify_add("is-browser", lambda *args: self.nb.set_current_page(0))

    def _update_pos(self, player, *args):        
        self._cur_view.playlist.set_cursor(player.playlist.pos)

    def _switch_to(self, caller, model):
        i = [v.playlist.get_model() for v in self._view].index(model)
        n = self.nb.page_num(self._view[i])
        self.nb.set_current_page(n)

    def add_playlist(self, playlist):
        pl = PlaylistView(playlist, self._controller, self.smenu, self.plmenu)
        self._view.append(pl)
        self.nb.append_page(pl, pl.label)
        self.nb.set_tab_reorderable(pl, True)
        self.nb.set_current_page(-1)

    def _move_lib_first(self, *args):
        self.nb.reorder_child(self._view[0], 0)

    def _change_playlist(self, nb, page, num, player):
        self._cur_view = nb.get_nth_page(num)
        player.playlist.set(self._cur_view.playlist.get_model())

    def show_notification(self, song):
        body = self.NOTIFY_STR.format(
                                    _("by"),
                                    xml_escape(song["artist"]),
                                    _("from"),
                                    xml_escape(song["album"]))
        self._notify.update(xml_escape(song["title"]), body)

        cover = song.cover_image((128, 128))
        
        if cover is None:
            cover = gtk.icon_theme_get_default().load_icon("audio-x-generic", 128, 0)
            
        self._notify.set_icon_from_pixbuf(cover)
        self._notify.show()
    
    def restore(self):
        for v in self._view:
            v.restore()
    
    def _watch_toggled(self, caller, state):
        self._toggle.handler_block(self._thndl)
        self._toggle.set_active(state)
        self._toggle.handler_unblock(self._thndl)
                  
    def _handle_keypress(self, widget, event):
        key = gtk.gdk.keyval_name(event.keyval)
        
        if key == "F11":
            self.window.toggle_fullscreen()
