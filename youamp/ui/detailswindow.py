import gtk

class CoverImage(gtk.Image):
    def __init__(self):
        gtk.Image.__init__(self)
        self.album = ""

    def set_generic(self):
        name = "audio-x-generic"
        pb = gtk.icon_theme_get_default().load_icon(name, self.size_request()[1], 0)
        self.set_from_pixbuf(pb)
        self.album = None

    def set_from_song(self, song, generic_fallback=True):
        pb = song.cover_image(self.size_request())

        if pb is None and generic_fallback:
            self.set_generic()
            return

        self.set_from_pixbuf(pb)
        self.album = song["album"]

class DetailsWindow(gtk.Window):
    __instance = None
    
    def __init__(self):
        if DetailsWindow.__instance is not None:
            raise Exception("This is a Singleton object")
        
        gtk.Window.__init__(self)
        self._create()
    
    @staticmethod
    def get_instance():
        if DetailsWindow.__instance is None:
            DetailsWindow.__instance = DetailsWindow()
        
        return DetailsWindow.__instance
    
    def _create(self):    
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.set_default_size(600, -1)
    
        self._data = None
        self._transl = (("title", _("Title")), 
                        ("artist", _("Artist")), 
                        ("album", _("Album")), 
                        ("playcount", _("Playcount")))
        
        ebox = gtk.EventBox()
        ebox.set_visible_window(False)
        self.add(ebox)
                
        # content
        hbox = gtk.HBox()
        hbox.set_spacing(5)
        ebox.add(hbox)
        
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
        
        ebox.connect("button-release-event", self.hide_on_delete)     
        self.connect("delete-event", self.hide_on_delete)
    
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
        self.set_title(_("Details for {0}").format(song["title"]))
        
        self._cover.set_from_song(song)
        self.set_icon_list(self._cover.get_pixbuf())
        
        for k, l in self._data.iteritems():
            l.set_text(str(song[k]))
        
        self._loc.set_text(song.uri)