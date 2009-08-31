import gtk
import time

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
                        
        config.notify_add("volume", self._on_conf_volume_changed)
        player.connect("seek-changed", lambda caller, new_seek: pos.set_value(new_seek))
        player.connect("toggled", lambda c, playing: tb.set_image(self.img[playing]))
   
    def _on_conf_volume_changed(self, client, cxn_id, entry, data):
        self.volume.set_value(entry.get_value().get_float())
    
    def _on_volume_changed(self, button, val, config):
        config["volume"] = val

class Icon:
    def __init__(self, player, xml):
        self._icon = xml.get_object("statusicon1")
        self._window = xml.get_object("window")
        
        self._menu = xml.get_object("icon_menu")

        player.connect("song-changed", self._update_songinfo)
        
        self._icon.connect("activate", self._toggle_window)
        self._icon.connect("popup-menu", self._popup_menu)
        
        self._hide_hndl = self._window.connect("window-state-event", self._ws_cb)
        self._window.handler_block(self._hide_hndl)
        self._iconified = False

    # hides window when it is iconified
    def _ws_cb(self, win, event):
        if event.new_window_state & gtk.gdk.WINDOW_STATE_ICONIFIED:
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
                                     32, gtk.gdk.PROP_MODE_REPLACE, icon_geom)

    def _popup_menu(self, caller, button, time):
        self._menu.popup(None, None, gtk.status_icon_position_menu, button, time, self._icon)
            
    def _update_songinfo(self, caller, newsong):
        text = "<b>{0}</b>\n{1} <i>{2}</i>".format(
                                                   xml_escape(newsong["title"]),
                                                   _("by"),
                                                   xml_escape(newsong["artist"]))
        self._icon.set_property("tooltip-markup", text)
    
    def _toggle_window(self, *args):        
        if not self._iconified:
            self._set_iconify_geometry()
            self._window.iconify()
            self._window.handler_unblock(self._hide_hndl)
        else:
            self._window.present()
            self._window.deiconify()

        self._iconified = not self._iconified
