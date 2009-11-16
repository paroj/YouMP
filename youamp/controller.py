import gtk
import gobject
import time
import urllib2
import sys
import dbus
import os.path
from dbus.mainloop.glib import DBusGMainLoop

from youamp import VERSION, Playlist, PlaylistMux
from youamp.ui.interface import UserInterface

from youamp.library import Library, check_db
from youamp.indexer import Indexer
from youamp.player import Player
from youamp.config import Config
import youamp.scrobbler as scrobbler

NM_STATE_CONNECTED = 3

class Controller:
    def __init__(self):
        check_db()
        DBusGMainLoop(set_as_default=True)
        self.config = Config("/apps/youamp/")
        check_config(self.config)
        self.player = Player(self.config)
        self.library = Library()
        indexer = Indexer()
        self.main_list = Playlist(None)
        self.main_list.title = _("Library")
        self.main_list.pos = self.config["pos"]
        self.jump_to = None
        self.player.playlist = PlaylistMux(self.main_list)

        gobject.set_application_name("YouAmp")

        # DBus Stuff
        session_bus = dbus.SessionBus()
        system_bus = dbus.SystemBus()

        # Network Manager
        nmanager = system_bus.get_object("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager")
        self._nm_props = dbus.Interface(nmanager, dbus_interface="org.freedesktop.DBus.Properties")

        # last.fm submission
        self.scrobbler = scrobbler.Scrobbler()
        self.scrobbler.connect("error", lambda c, t, m: sys.stderr.write("scrobbler: "+m+"\n"))
        self.scrobbler.login(self.config["lastfm-user"], self.config["lastfm-pass"], ("you", VERSION))
                
        # MMKeys
        mmkeys = session_bus.get_object("org.gnome.SettingsDaemon", "/org/gnome/SettingsDaemon/MediaKeys")
        mmkeys.connect_to_signal("MediaPlayerKeyPressed", self._handle_mmkeys)
        
        self.gui = UserInterface(self)
        
        self._restore()
        
        self.player.connect("song-played", self._on_song_played)
        self.config.notify_add("music-folder", self._set_new_playlist)
        self.config.notify_add("is-browser", self._set_new_playlist)
        self.player.connect("song-changed", self._now_playing)
        self.player.connect("song-changed", self._update_pos)
        
        indexer.connect("update-complete", self._on_index_updated)
        
        index_dirs = [os.path.expanduser("~")]
        
        if not self.config["music-folder"].startswith(index_dirs[0]):
            index_dirs += [self.config["music-folder"]]
        
        indexer.update(index_dirs)

    def _update_pos(self, player, *args):
        if player.playlist is self.main_list:
            self.config["pos"] = self.main_list.pos

    def _on_index_updated(self, caller, was_updated):        
        if was_updated:
            gobject.idle_add(self._refresh_playlist)

    def _restore(self):
        self._refresh_playlist()
 
        if self.config["shuffle"]:
            self.player.playlist.shuffle(True)

        # restore playlist pos
        try:
            self.player.load_track()
        except IndexError:
            # track might have been deleted
            pass
        
        self.gui.restore()
        
    def _handle_mmkeys(self, s1, key):
        action = dict()
        action["Play"] = self.player.toggle
        action["Previous"] = self.player.previous
        action["Next"] = self.player.next
        
        action[key]()
    
    def set_list_order(self, order):
        if order in ("album", "playcount"):
            self.main_list.order_by(order)
            return

        self.config["order-by"] = order
        self.config["shuffle"] = False
        self.config["pos"] = 0
        
        self._refresh_playlist()
    
    def _set_new_playlist(self, *args):        
        self._refresh_playlist()
        
        if self.config["shuffle"]:
            self.main_list.shuffle(True)
        
        self.config["pos"] = 0
    
    def _refresh_playlist(self):
        playlist = self.library.get_tracks(self.config)
            
        self.main_list.update(playlist)

    def _on_song_played(self, player, song):
        played = player.get_time()
        
        # workaround for bugged maemo
        if not "duration" in song:
            return
        
        if (played < song["duration"]/2 and played < 240) or song["duration"] < 30:
            return
        
        # call library from main thread
        gobject.idle_add(self.library.increment_played, song.uri)

        nm_connected = self._nm_props.Get("org.freedesktop.NetworkManager", "State") == NM_STATE_CONNECTED

        if self.scrobbler.is_connected() and nm_connected:
            self.scrobbler.submit(song["artist"], song["title"], int(time.time()), album=song["album"], length=song["duration"])
        else:
            sys.stderr.write("scrobbler: song {0} discarded\n nm_connected: {1}\n".format(song["title"], nm_connected))
                

    def _now_playing(self, player, song):        
        if not self.gui.window.visible():
            self.gui.show_notification(song)

        nm_connected = self._nm_props.Get("org.freedesktop.NetworkManager", "State") == NM_STATE_CONNECTED

        if self.scrobbler.is_connected() and nm_connected:
            self.scrobbler.now_playing(song["artist"], song["title"], song["album"])
        else:
            sys.stderr.write("now playing: song {0} discarded\n nm_connected: {1}\n".format(song["title"], nm_connected))

    def start(self):
        gtk.main()
        
    def quit(self, *args):
        # submit to last.fm
        if self.scrobbler.is_connected():
            try:
                self.scrobbler.flush()
            except urllib2.URLError, e:
                sys.stderr.write("lastfm.submit: %s\n" % e)
        
        gtk.main_quit()

def check_config(config):
    if not "volume" in config:
        # write default config
        config["volume"] = 0.5
        config["search-str"] = ""
        config["search-artist"] = ""
        config["search-album"] = ""
        config["pos"] = 0
        config["shuffle"] = False
        config["is-browser"] = False
        config["rg-preamp"] = 0     # preamp to adjust the default of 89db (value: db)
        config["no-rg-preamp"] = -10  # amp value to be used if no rg info is available (value: db)
    
    # order by was added in v0.3.5, therefore check for it seperately
    if not "order-by" in config:
        config["order-by"] = "album"

    # order by renamed in v0.5.8
    if config["order-by"] == "artist":
        config["order-by"] = "album"

    # music-folder was added in v0.3.8
    if not "music-folder" in config:
        config["music-folder"] = os.path.expanduser("~")
        
    # last.fm support was added in v0.4.0
    if not "lastfm-user" in config:
        config["lastfm-user"] = ""
        config["lastfm-pass"] = ""

    # added in v0.6.0
    if not "gapless" in config:
        config["gapless"] = True
