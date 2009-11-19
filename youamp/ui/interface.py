import gtk
import pynotify
import gtk.gdk

from youamp.ui.window import Window
from youamp.ui.preferences import Preferences
from youamp.ui.searchview import SearchView

from youamp.ui.playlist import PlaylistView, PlaylistMenu
from youamp.ui.popupmenu import SongMenu

from youamp.ui.elements import *
from youamp.ui import xml_escape

from youamp import VERSION, data_path

class UserInterface:
    NOTIFY_STR = "{0} <i>{1}</i>\n{2} <i>{3}</i>"

    def __init__(self, controller):
        player = controller.player
        config = controller.config
        library = controller.library
        scrobbler = controller.scrobbler
        
        # Build Interface
        xml = gtk.Builder()
        xml.set_translation_domain("youamp")
        xml.add_from_file(data_path + "interface.ui")

        # Create Views
        smenu = SongMenu(config, player, xml)
        plmenu = PlaylistMenu(xml)

        self._view = [SearchView(controller.main_list, player, library, config, smenu, xml)]
        self._cur_view = self._view[0]

        lists = [PlaylistView(l, player, controller, smenu, plmenu) for l in library.get_playlists()]
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

        if not config["shuffle"]:
            xml.get_object("order_"+config["order-by"]).set_active(True)

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
            self.nb.append_page(v.view, v.label)
        
        for lv in lists:
            self.nb.set_tab_reorderable(lv.view, True)

        # disable implicit playlist change
        self.nb.connect("switch-page", self._change_playlist, player)
        self.nb.connect("page-reordered", self._move_lib_first)

        # Signals
        xml.connect_signals({"show-preferences": lambda *args: prefs.cshow(),
                             "show-about": lambda *args: about.show(),
                             "order-album": lambda caller: controller.set_list_order("album"),
                             "order-date": lambda caller: controller.set_list_order("date"),
                             "order-playcount": lambda caller: controller.set_list_order("playcount"),
                             "quit": controller.quit,
                             "key-press": self._handle_keypress,
                             "hide-on-delete": gtk.Widget.hide_on_delete,
                             "toggle": lambda caller: player.toggle(),
                             "previous": lambda caller: player.previous(),
                             "next": lambda caller: player.next(),
                             "seek-change": lambda caller, *a: player.seek_to(caller.get_value()),
                             "view-search": lambda caller: self._cur_view.search_mode(),
                             "view-browse": lambda caller: self._cur_view.browse_mode(),
                             "select-current": lambda caller: self._cur_view.restore(),
                             "new-playlist": lambda caller: self.new_playlist(config, player, library, smenu, plmenu)})

        self._toggle = xml.get_object("playback_item")
        self._thndl = self._toggle.connect("toggled", lambda caller: player.toggle())
        player.connect("toggled", self._watch_toggled)
        player.playlist.connect("list-switched", self._switch_to)
        
        # change to library on browsing
        config.notify_add("is-browser", lambda *args: self.nb.set_current_page(0))

    def _switch_to(self, caller, model):
        i = [e.get_model() for e in self._view].index(model)
        n = self.nb.page_num(self._view[i].view)
        self.nb.set_current_page(n)

    def new_playlist(self, config, player, library, smenu, plmenu):
        pl = PlaylistView(library.get_new_playlist(), player, library, smenu, plmenu)
        self._view.append(pl)
        self.nb.append_page(pl.view, pl.label)
        self.nb.set_tab_reorderable(pl.view, True)
        self.nb.set_current_page(-1)

    def _move_lib_first(self, *args):
        self.nb.reorder_child(self._view[0].view, 0)

    def _change_playlist(self, nb, page, num, player):
        self._cur_view = nb.get_nth_page(num).top
        player.playlist.set(self._cur_view.view.playlist)

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
