import gtk
import gst
import pango
import os.path

from youamp import KNOWN_EXTS
from youamp.playlist import Song

class ListView(gtk.TreeView):
    SOURCE = [("text/x-youamp-reorder", gtk.TARGET_SAME_WIDGET, 0),
              ("text/uri-list", gtk.TARGET_SAME_APP, 1),
              ("text/uri-list", 0, 2)]

    SINK = SOURCE

    def __init__(self, list):
        gtk.TreeView.__init__(self, list)

        self.set_rules_hint(True)
        self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.set_fixed_height_mode(True)

        # drag and drop
        self.enable_model_drag_dest(self.SINK, gtk.gdk.ACTION_LINK)
        self.enable_model_drag_source(gtk.gdk.BUTTON1_MASK, self.SOURCE, gtk.gdk.ACTION_COPY)

        self.connect_after("drag-begin", self._drag_begin)
        self.connect("drag-data-received", self._recieve_drag_data)
        self.connect("drag-data-get", self._get_drag_data)
        self.connect("drag-data-delete", self._delete_drag_data)

    def _drag_begin(self, caller, ctx):
        num = self.get_selection().count_selected_rows()

        icon = gtk.STOCK_DND_MULTIPLE if num > 1 else gtk.STOCK_DND

        ctx.set_icon_stock(icon, 0, 0)

    def _get_drag_data(self, tv, ctxt, selection, info, time):
        model, paths = self.get_selection().get_selected_rows()

        uris = []

        for p in paths:
            uris.append(self.uri_from_path(p))

        selection.set("text/uri-list", 8, "\n".join(uris))

    def _recieve_drag_data(self, tv, ctxt, x, y, selection, info, time):
        # disable reorder
        #if info == 0:
        #    ctxt.finish(False, False, time)
        #    return

        drop_info = self.get_dest_row_at_pos(x, y)

        model = self._model
        uris = selection.get_uris()

        if drop_info is not None:
            path, pos = drop_info
            itr = model.get_iter(path)
            if pos in (gtk.TREE_VIEW_DROP_BEFORE, gtk.TREE_VIEW_DROP_INTO_OR_BEFORE):
                self._handle_uri_drop(uris, before=itr)
            else:
                self._handle_uri_drop(uris, after=itr)
        else:
            self._handle_uri_drop(uris)

        ctxt.finish(True, info == 0, time)

    def _delete_drag_data(self, caller, ctx):
        model, paths = self.get_selection().get_selected_rows()
        paths = [model.get_iter(p) for p in paths]

        model.remove(paths)

    def _button_press(self, caller, ev):
        try:
            path = self.get_path_at_pos(int(ev.x), int(ev.y))[0]
        except TypeError:
            # path is None => no row at cursor position
            return

        if ev.button == 3:
            self._popup_menu(ev)
        elif ev.button == 1:
            # block selection action when clicking on multiple slected rows
            # => allows dnd of multiple rows
            sel = self.get_selection()

            allow_sel = sel.count_selected_rows() <= 1 \
                        or not sel.path_is_selected(path) \
                        or ev.state & (gtk.gdk.SHIFT_MASK|gtk.gdk.CONTROL_MASK)

            sel.set_select_function(lambda *args: allow_sel)

class SongList(ListView):
    # FIXME: reordering same playlist results in DBus call for tracker

    def __init__(self, playlist, player, library, menu):
        ListView.__init__(self, playlist)

        self._player = player
        self._library = library
        self._model = playlist

        self.set_headers_visible(True)

        transl = (("title", _("Title")),
                  ("artist", _("Artist")),
                  ("album", _("Album")))

        cell = gtk.CellRendererText()
        cell.set_property("ellipsize", pango.ELLIPSIZE_END)

        for key, title in transl:
            col = gtk.TreeViewColumn(title, cell)
            col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            col.set_resizable(True)
            col.set_fixed_width(266)
            col.set_min_width(100)
            col.set_cell_data_func(cell, self._data_func, key)
            self.append_column(col)

        # menu
        self._menu = menu
        self.connect("button-press-event", self._button_press)

        # Signals
        player.connect("song-changed", self._on_pos_changed)
        self.connect("row-activated", self._on_row_activated)

    def restore(self):
        if len(self._model) > 0:
            self._on_pos_changed()

    def _popup_menu(self, ev):
        pos = self.get_path_at_pos(int(ev.x), int(ev.y))[0]

        self._menu.song = self._model[pos]
        self._menu.playlist = self
        self._menu.pos = pos
        self._menu.popup(None, None, None, ev.button, ev.time)
    
    def _handle_uri_drop(self, uris, before=None, after=None):     
        paths = []
        
        # FIXME Controller functionality
        for uri in uris:
            path = gst.uri_get_location(uri)
            
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for f in files:
                        if f.lower().endswith(KNOWN_EXTS):
                            path = os.path.join(root, f)
                            paths.append(path)
            else:
                paths.append(path)
        
        songs = [self.song_from_path(p) for p in paths]
        
        if before is not None:
            self._model.insert_before(before, songs)
        elif after is not None:
            self._model.insert_after(after, songs)
        else:
            self._model.append(songs)
    
    def song_from_path(self, path):
        return Song(self._library.get_metadata(path))

    def uri_from_path(self, path):
        return "file://"+self._model[path].uri

    def _on_pos_changed(self, player=None, *args):
        # if player is None we are called by user
        if player is None or player.playlist == self._model:
            self.set_cursor(self._model.pos)

    def _on_row_activated(self, caller, path, column):
        self._player.playlist.set(self._model)

        self._player.goto_pos(path[0])

    def _data_func(self, col, cell, model, itr, key):
        v = model[itr][key]
        v = v if v != "" else _("None")
        cell.set_property("text", v)
