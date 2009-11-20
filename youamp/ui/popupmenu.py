from youamp.ui.playlist import PlaylistView
from youamp.ui.detailswindow import DetailsWindow

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

class SongMenu:
    def __init__(self, config, player, xml):
        self._w = xml.get_object("context_menu")
        
        self.song = None
        self.playlist = None
        self.pos = None
        self._details = DetailsWindow.get_instance()
            
        self._config = config
        
        enq = xml.get_object("play_next")
        enq.connect("activate", self._jump_next_to, player)
                
        bar = xml.get_object("view_artist")
        bar.connect("activate", self._browse_artist)
        
        bal = xml.get_object("view_album")
        bal.connect("activate", self._browse_album)

        self.rem = xml.get_object("remove_song")
        self.rem.connect("activate", self._remove)

        details = xml.get_object("view_details")
        details.connect("activate", self._display_details)

    def popup(self, *args):
        self._w.popup(*args)

    def _remove(self, *args):
        m = self.playlist.get_model()
        m.remove(m.get_iter(self.pos))

    def _jump_next_to(self, caller, player):
        player.playlist.jump_to = (self.playlist.get_model(), self.song)
        
    def _browse_artist(self, *args):
        self._config["search-artist"] = str(self.song["artist"])
        self._config["search-album"] = "" 
        self._config["is-browser"] = True
        self._config.notify("is-browser")

    def _browse_album(self, *args):
        self._config["search-artist"] = ""
        self._config["search-album"] = str(self.song["album"])
        self._config["is-browser"] = True
        self._config.notify("is-browser")
 
    def _display_details(self, *args):
        self._details.set_data(self.song)
        self._details.show_all()
