from youamp.ui.detailswindow import CoverImage
from youamp.ui import xml_escape

class Window:
    def __init__(self, player, dw, sm, xml):
        self._w = xml.get_object("window")
        self._player = player
        self._sm = sm
        self._last_album = None
        self.iconified = False
        
        self._is_fullscreen = False
        self._ftoggle = xml.get_object("toggle_fullscreen")
        self._fthndl = self._ftoggle.connect("activate", lambda caller: self.toggle_fullscreen())
                       
        # Cover
        evbox = xml.get_object("cover_evbox")
        self._cover = CoverImage()
        evbox.add(self._cover)
        evbox.connect("button-press-event", self._display_details)
        
        # Details
        self._details = dw
        
        # Label
        self._label = xml.get_object("track_label")
        self._label.set_markup("<b><big>{0}</big></b>\n".format(_("No Track")))
                    
        r, n = xml.get_object("hbox2").get_preferred_size()
        self._cover.set_size_request(r.height, r.height)
    
        self._player.connect("song-changed", self._update_songinfo)
        self._sm.connect("new-cover", self._update_cover)
        
        self._cover.show()
        self._w.show()

    def is_active(self):
        return self._w.get_property("is-active")
    
    def _display_details(self, *args):
        self._details.set_data(self._player._current)
        self._details.show_all()
            
    def iconify(self):
        if self.iconified:
            return
        
        self._w.iconify()
        self._w.hide()
        self.iconified = True
    
    def present(self):
        self._w.present()
        self._w.deiconify()
        self.iconified = False
        
    def toggle_fullscreen(self):
        if self._is_fullscreen:
            self._w.unfullscreen()
        else:
            self._w.fullscreen()
        
        self._is_fullscreen = not self._is_fullscreen
        
        self._ftoggle.handler_block(self._fthndl)
        self._ftoggle.set_active(self._is_fullscreen)
        self._ftoggle.handler_unblock(self._fthndl)
    
    def _update_cover(self, caller, path, album):
        if album != self._last_album:
            return
        
        self._cover.set_from_path(path)
        
    def _update_songinfo(self, caller, newsong):
        self._w.set_title("{0} - {1}".format(newsong["title"], newsong["artist"]))
                
        label_txt = "<b><big>{0}</big></b> {1} <i>{2}</i>\n{3} <i>{4}</i>"
        label_txt = label_txt.format(
                                     xml_escape(newsong["title"]),
                                     _("by"),
                                     xml_escape(newsong["artist"]),
                                     _("from"),
                                     xml_escape(newsong["album"]))
        
        if not self._player.has_rg_info():
            label_txt = """<span foreground="red">{0}</span>""".format(label_txt)
        
        self._label.set_markup(label_txt)
        
        # image        
        if newsong["album"] == self._last_album and newsong["album"] != _("None"):
            return
        
        self._cover.set_from_path(self._sm.get_cover_path(newsong))
        self._last_album = newsong["album"]
            
        #self._w.set_icon_list(self._cover.get_pixbuf())
