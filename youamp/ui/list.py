from gi.repository import Gtk, Gdk

class ListView(Gtk.TreeView):
    SOURCE = [("text/x-youamp-reorder", Gtk.TargetFlags.SAME_WIDGET, 0),
              ("text/uri-list", Gtk.TargetFlags.SAME_APP, 1),
              ("text/uri-list", 0, 2)]

    SINK = SOURCE

    def __init__(self, list):
        Gtk.TreeView.__init__(self, list)

        self.set_rules_hint(True)
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.set_fixed_height_mode(True)

        # drag and drop
        self.enable_model_drag_dest(self.SINK, Gdk.DragAction.LINK)
        self.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, self.SOURCE, Gdk.DragAction.COPY)

        self.connect_after("drag-begin", self._drag_begin)
        self.connect("drag-data-received", self._recieve_drag_data)
        self.connect("drag-data-get", self._get_drag_data)
        self.connect("drag-data-delete", self._delete_drag_data)

    def _drag_begin(self, caller, ctx):
        num = self.get_selection().count_selected_rows()

        icon = Gtk.STOCK_DND_MULTIPLE if num > 1 else Gtk.STOCK_DND

        Gtk.drag_set_icon_stock(ctx, icon, 0, 0)

    def _get_drag_data(self, tv, ctxt, selection, info, time):
        model, paths = self.get_selection().get_selected_rows()

        uris = self.get_uris(paths)

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
            if pos in (Gtk.TreeViewDropPosition.BEFORE, Gtk.TreeViewDropPosition.INTO_OR_BEFORE):
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
        sel = self.get_selection()
        
        try:
            path = self.get_path_at_pos(int(ev.x), int(ev.y))[0]
        except TypeError:
            # path is None => no row at cursor position
            sel.set_select_function(lambda *args: True, None)
            sel.unselect_all()
            return

        # block selection action when clicking on multiple slected rows
        # => allows dnd of multiple rows
        allow_sel = sel.count_selected_rows() <= 1 \
                    or not sel.path_is_selected(path) \
                    or ev.state & (Gdk.ModifierType.SHIFT_MASK|Gdk.ModifierType.CONTROL_MASK)

        sel.set_select_function(lambda *args: allow_sel, None)
        
        if ev.button == 3:
            self._popup_menu(ev)
