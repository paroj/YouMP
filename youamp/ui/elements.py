from gi.repository import Gtk
import time

HAS_APPINDICATOR = False

from youamp.ui import xml_escape

class Controls:
    def __init__(self, player, config, xml):        
        # is playing
        self.img = dict()
        self.img[False] = xml.get_object("image_play")
        self.img[True] = xml.get_object("image_pause")

        tb = xml.get_object("toggle_button")
        pos = xml.get_object("seek")
                
        self.volume = xml.get_object("volume_button")
        self.volume.set_value(config["volume"])
        self.volume.connect("value-changed", self._on_volume_changed, config)
                        
        config.connect("changed::volume", self._on_conf_volume_changed)
        player.connect("seek-changed", lambda caller, new_seek: pos.set_value(new_seek))
        player.connect("toggled", lambda c, playing: tb.set_image(self.img[playing]))
        
        pos.connect("button-press-event", self._on_seek_click)
        pos.connect("button-release-event", self._on_seek_click)
   
    def _on_seek_click(self, scale, ev):
        # forces jump to pos
        ev.button = 2
   
    def _on_conf_volume_changed(self, client, entry):
        self.volume.set_value(client[entry])
    
    def _on_volume_changed(self, button, val, config):
        config["volume"] = val

class Icon:
    def __init__(self, player, window, xml):
        self._icon = xml.get_object("statusicon1")
        vis_menu_toggle = xml.get_object("vis_menu_toggle")
                                
        self._menu = xml.get_object("icon_menu")

        self._window = window._w
        self.win = window

        if HAS_APPINDICATOR:
            self._icon.set_visible(False)   
            
            self._ind = appindicator.Indicator ("youamp", "youamp",
                            appindicator.CATEGORY_APPLICATION_STATUS)
            
            self._ind.set_status(appindicator.STATUS_ACTIVE)
            self._ind.set_menu(self._menu)
            
            vis_menu_toggle.connect("toggled", self._toggle_window_ind)
        else:
            vis_menu_toggle.hide()
            sep = xml.get_object("menuitem3")
            sep.hide()
            
            self._icon.connect("activate", self._toggle_window)
            self._icon.connect("popup-menu", self._popup_menu)
            
            self._hide_hndl = self._window.connect("window-state-event", self._ws_cb)
            self._window.handler_block(self._hide_hndl)

        player.connect("song-changed", self._update_songinfo)

    # hides window when it is iconified
    def _ws_cb(self, win, event):
        if event.new_window_state & Gdk.WindowState.ICONIFIED:
            if win.is_composited():
                # FIXME: workaround for compiz bug
                time.sleep(0.25)
                
            win.hide()
            win.handler_block(self._hide_hndl)

    def _set_iconify_geometry(self):
        # tell window to iconify to tray icon
        g = self._icon.get_geometry()[1]
        icon_geom = (g.x, g.y, g.width, g.height)
        self._window.window.property_change("_NET_WM_ICON_GEOMETRY", "CARDINAL", \
                                     32, Gdk.PropMode.REPLACE, icon_geom)

    def _popup_menu(self, caller, button, time):
        self._menu.popup(None, None, Gtk.status_icon_position_menu, button, time, self._icon)
            
    def _update_songinfo(self, caller, newsong):
        text = "<b>{0}</b>\n{1} <i>{2}</i>".format(
                                                   xml_escape(newsong["title"]),
                                                   _("by"),
                                                   xml_escape(newsong["artist"]))
        self._icon.set_property("tooltip-markup", text)
    
    def _toggle_window_ind(self, *args):
        if not self.win.iconified:
            self.win.iconify()
        else:
            self.win.present()

    def _toggle_window(self, *args):   
        if not self.win.iconified:
            self._set_iconify_geometry()
            self._window.iconify()
            self._window.handler_unblock(self._hide_hndl)
        else:
            self._window.present()
            self._window.deiconify()

        self.win.iconified = not self.win.iconified

class PlaylistLabel(Gtk.EventBox):
    def __init__(self, playlist=None, icon="audio-x-generic"):
        Gtk.EventBox.__init__(self)

        self.set_visible_window(False)

        hbox = Gtk.HBox()
        self.add(hbox)
        hbox.set_spacing(2)
        #hbox.pack_start(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU))

        self.entry = Gtk.Entry()
        self.entry.set_has_frame(False)
        self.label = Gtk.Label()
        self.playlist = playlist
        self.editing = False
        self.just_created = False

        hbox.pack_start(self.label, True, True, 0)
        hbox.pack_start(self.entry, True, True, 0)

        hbox.show_all()

        r, n = self.label.get_preferred_size()
        self.entry.set_size_request(-1, r.height)

        if playlist.title is None:
            playlist.title = _("New Playlist")
            self.just_created = True
            self.edit_name()
        else:
            self.entry.hide()
            self.label.set_text(playlist.title)

        self.entry.connect("activate", self._set_name)
        self.entry.connect("focus-out-event", self._set_name)
        self.entry.connect_after("map-event", lambda caller, *a: caller.grab_focus())
    
    def edit_name(self):
        self.label.hide()
        self.editing = True
        self.entry.set_text(self.playlist.title)
        self.entry.show()
    
    def _set_name(self, caller, *args):
        self.entry.hide()
        self.editing = False
        new_title = caller.get_text()
        self.label.set_text(new_title)

        if self.just_created:
            self.just_created = False

        self.playlist.rename(new_title)

        self.label.show()
