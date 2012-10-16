from gi.repository import Gtk, Gdk, Pango

from youamp.ui.list import ListView
from youamp.ui.elements import PlaylistLabel

class SongsTab(Gtk.VBox):
    def __init__(self, playlist, controller, menu):
        Gtk.VBox.__init__(self)
        self.set_spacing(5)

        self.label = PlaylistLabel(playlist)
        
        self._navi = Gtk.HBox()
        self._navi.set_spacing(5)
        self._navi.set_border_width(5)
        self.pack_start(self._navi, False, True, 0)

        # Order Combo
        self.order = Gtk.ComboBoxText()
        self.order.append_text(_("album"))
        self.order.append_text(_("playcount"))
        self.order.append_text(_("date added"))
        self.order.append_text(_("shuffle"))
        # disable change by scrolling -> too expensive
        self.order.connect("scroll-event", lambda *args: True)

        self._navi.pack_end(self.order, False, True, 0)
        self._navi.pack_end(Gtk.Label(label=_("Order:")), False, True, 0)

        # Scrolled View
        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
        self._scroll.set_shadow_type(Gtk.ShadowType.IN)
        
        self.playlist = SonglistView(playlist, controller, menu)
        self._scroll.add(self.playlist)

        self.pack_start(self._scroll, True, True, 0)

class SonglistView(ListView):
    def __init__(self, playlist, controller, menu):
        ListView.__init__(self, playlist)

        self._model = playlist

        self.set_headers_visible(True)

        transl = (("title", _("Title")),
                  ("artist", _("Artist")),
                  ("album", _("Album")))

        cell = Gtk.CellRendererText()
        cell.set_property("ellipsize", Pango.EllipsizeMode.END)

        for key, title in transl:
            col = Gtk.TreeViewColumn(title, cell)
            col.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            col.set_resizable(True)
            col.set_fixed_width(266)
            col.set_min_width(100)
            col.set_cell_data_func(cell, self._data_func, key)
            self.append_column(col)
        
        # menu
        self._menu = menu
        self.connect("button-press-event", self._button_press)

        # Signals
        self.connect("row-activated", controller.song_selected)
        
        # redirect to controller
        self._handle_uri_drop = lambda *args, **kwargs: controller.on_uri_drop(playlist, *args, **kwargs)
    
    def restore(self):
        if len(self._model) > 0:
            self.select_current()

    def _popup_menu(self, ev):
        self._menu.rem.set_sensitive(self._model.backend is not None)
        
        pos = self.get_path_at_pos(int(ev.x), int(ev.y))[0]

        self._menu.song = self._model[pos]
        self._menu.playlist = self._model
        self._menu.remove_act = self.remove_selection
        self._menu.popup(None, None, None, None, ev.button, ev.time)

    def remove_selection(self):
        model, paths = self.get_selection().get_selected_rows()
        paths = [model.get_iter(p) for p in paths]

        model.remove(paths)
            
    def get_uris(self, paths):
        return ["file://"+self._model[p].uri for p in paths]
    
    def select_current(self):
        self.set_cursor(self._model.pos)

    def _data_func(self, col, cell, model, itr, key):
        v = model[itr][key]
        cell.set_property("text", v)

class PlaylistView(SongsTab):    
    def __init__(self, playlist, controller, song_menu, pl_menu):
        SongsTab.__init__(self, playlist, controller, song_menu)
        
        self._controller = controller
        self.order.set_active(0)
        self.order.connect("changed", self._on_order_changed)
        
        self.label.drag_dest_set(Gtk.DestDefaults.ALL, [Gtk.TargetEntry.new(*t) for t in self.playlist.SINK[2:3]], Gdk.DragAction.COPY)
        self.label.connect("drag-data-received", self.playlist._recieve_drag_data)

        self.menu = pl_menu

        self.label.connect("button-press-event", self.__popup_menu)
        self.connect("key-press-event", self._on_key_press)
        
        self.show_all()
    
    def restore(self):
        self.playlist.restore()
    
    def _on_key_press(self, caller, ev):
        key = Gdk.keyval_name(ev.keyval)

        if key == "Delete":
            self.playlist.remove_selection()

    def _on_order_changed(self, caller):   
        self._controller.order_changed(caller, self.playlist.get_model())   
        self.playlist.select_current()

    def remove(self):
        self.playlist._model.delete()
        self.destroy()

    def __popup_menu(self, caller, ev):
        if ev.button == 3 and not self.label.editing:
            self.menu.view = self
            self.menu.popup(None, None, None, None, ev.button, ev.time)
