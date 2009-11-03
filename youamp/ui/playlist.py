import gtk
import gtk.gdk

from youamp.ui.list import SongList

class PlaylistLabel(gtk.EventBox):
    def __init__(self, playlist=None, icon="audio-x-generic"):
        gtk.EventBox.__init__(self)

        self.set_visible_window(False)

        hbox = gtk.HBox()
        self.add(hbox)
        hbox.set_spacing(2)
        hbox.pack_start(gtk.image_new_from_icon_name(icon, gtk.ICON_SIZE_MENU))

        self.entry = gtk.Entry()
        self.entry.set_has_frame(False)
        self.label = gtk.Label()
        self.playlist = playlist
        self.editing = False
        self.just_created = False

        hbox.pack_start(self.label)
        hbox.pack_start(self.entry)

        hbox.show_all()

        h = self.label.size_request()[1]
        self.entry.set_size_request(-1, h)

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
            self.playlist.title = new_title
            self.playlist.save()
            self.just_created = False
        else:
            self.playlist.rename(new_title)

        self.label.show()

class PlaylistMenu:
    def __init__(self, xml):
        self._w = xml.get_object("playlist_menu")

        self.view = None

        xml.get_object("playlist_rename").connect("activate", self._rename)
        xml.get_object("playlist_delete").connect("activate", self._remove)

    def _rename(self, caller):
        self.view.label.edit_name()

    def _remove(self, caller):
        self.view.remove()

    def popup(self, *args):
        self._w.popup(*args)

class PlaylistView(SongList):
    def __init__(self, playlist, player, library, song_menu, pl_menu):
        SongList.__init__(self, playlist, player, library, song_menu)

        self.view = gtk.VBox()
        self.view.set_spacing(5)
        self.view.top = self
        hbox = gtk.HBox()
        
        shuffle = gtk.ToggleButton(_("shuffle"))
        shuffle.connect("toggled", self._on_shuffle_toggled)
        
        hbox.pack_end(shuffle, expand=False)
        
        self.view.pack_start(hbox, expand=False)

        sw = gtk.ScrolledWindow()
        self.view.pack_start(sw)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(self)

        self.view.playlist = playlist
        self.view.restore = self.restore


        self.label = PlaylistLabel(playlist)
        self.label.drag_dest_set(gtk.DEST_DEFAULT_ALL, self.SINK[2:3], gtk.gdk.ACTION_COPY)
        self.label.connect("drag-data-received", self._recieve_drag_data)

        self.menu = pl_menu

        self.label.connect("button-press-event", self.__popup_menu)
        self.connect("key-press-event", self._on_key_press)
        self.view.show_all()
    
    def _on_shuffle_toggled(self, caller):
        self._model.shuffle(caller.get_active())
        
        self._model.pos = self._model.get_new_pos(self._model.pos)
        self.set_cursor(self._model.pos)
    
    def _on_key_press(self, caller, ev):
        key = gtk.gdk.keyval_name(ev.keyval)

        if key == "Delete":
            model, paths = self.get_selection().get_selected_rows()
            paths = [model.get_iter(p) for p in paths]

            for p in paths:
                model.remove(p)

    def remove(self):
        self._model.delete()
        self.view.destroy()

    def __popup_menu(self, caller, ev):
        if ev.button == 3 and not self.label.editing:
            self.menu.view = self
            self.menu.popup(None, None, None, ev.button, ev.time)