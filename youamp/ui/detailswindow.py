import gtk

class CoverImage(gtk.Image):
    def __init__(self):
        gtk.Image.__init__(self)

    def set_generic(self):
        name = "audio-x-generic"
        pb = gtk.icon_theme_get_default().load_icon(name, self.size_request()[1], 0)
        self.set_from_pixbuf(pb)

    def set_from_path(self, path):
        if path is None:                
            self.set_generic()
            return
        
        pb = gtk.gdk.pixbuf_new_from_file_at_size(path, *self.size_request())       
        self.set_from_pixbuf(pb)

class DetailsWindow:    
    def __init__(self, song_meta, xml):
        self._w = xml.get_object("details_window")
                      
        self._sm = song_meta
        
        xml.get_object("details_ebox").connect("button-release-event", self._w.hide_on_delete)
    
        self._data = None
        self._transl = (("title", _("Title")),
                        ("artist", _("Artist")),
                        ("album", _("Album")),
                        ("playcount", _("Playcount")))
                
        # content
        hbox = xml.get_object("details_hbox")
        
        self._cover = CoverImage()
        self._cover.set_size_request(300, 300)
        hbox.pack_start(self._cover, expand=False)
        
        dbox = gtk.VBox()
        hbox.pack_start(dbox)
        
        self._data = {}
        
        for k, tk in self._transl:
            row, self._data[k] = self._data_row(tk)
            dbox.pack_start(row, expand=False)
            
        row, self._loc = self._data_row(_("Location"))
        dbox.pack_start(row, expand=False)
    
    def show_all(self):
        self._w.show_all()
    
    def _data_row(self, tk):
        row = gtk.HBox()
        
        kl = gtk.Label()
        kl.set_markup("<b>{0}</b>".format(tk))
        kl.set_size_request(120, -1)
        kl.set_alignment(0, 0)
        row.pack_start(kl, expand=False)
        
        dlabel = gtk.Label()
        dlabel.set_alignment(0, 0.5)
        dlabel.set_line_wrap(True)
        dlabel.set_size_request(280, -1)
        row.pack_start(dlabel)
        
        return row, dlabel
            
    def set_data(self, song):
        self._w.set_title(_("Details for {0}").format(song["title"]))
        
        self._cover.set_from_path(self._sm.get_cover_path(song))
        #self._w.set_icon_list(self._cover.get_pixbuf())
        
        for k, l in self._data.iteritems():
            l.set_text(str(song[k]))
        
        self._loc.set_text(song.uri)