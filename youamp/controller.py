from gi.repository import GObject, Gtk, Gio

import time
import urllib.request, urllib.error, urllib.parse
import sys
import dbus
import os.path

from dbus.bus import REQUEST_NAME_REPLY_PRIMARY_OWNER
from dbus.mainloop.glib import DBusGMainLoop

from youamp import VERSION, KNOWN_EXTS
from youamp.ui.interface import UserInterface

from youamp.playlist import Playlist, PlaylistMux, Song
from youamp.library import Library, check_db
from youamp.indexer import Indexer
from youamp.songmeta import SongMetaLastFM
from youamp.player import Player

from youamp.soundmenu import SoundMenuControls

import youamp.scrobbler as scrobbler

NM_STATE_CONNECTED = 3

class Controller:
    ORDER_MAPPING = ("album", "playcount", "date", "shuffle")
    
    def __init__(self):
        check_db()
        DBusGMainLoop(set_as_default=True)
        self.config = Gio.Settings("net.rojtberg.youamp")
        self.player = Player(self.config)
        self.library = Library()
        self.song_meta = SongMetaLastFM()
        indexer = Indexer()
        self.main_list = Playlist(None)
        self.main_list.title = _("Library")
        self.main_list.pos = self.config["pos"]
        self.jump_to = None
        self.player.playlist = PlaylistMux(self.main_list)

        GObject.set_application_name("YouAmp")

        # DBus Stuff
        session_bus = dbus.SessionBus()
        system_bus = dbus.SystemBus()
        
        ret = session_bus.request_name("org.mpris.MediaPlayer2.youamp-player")
        
        self._already_running = (ret != REQUEST_NAME_REPLY_PRIMARY_OWNER)
        
        if self._already_running:
            return

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
        
        # MPRIS
        self.sound_menu = SoundMenuControls("youamp-player")
        self.sound_menu._sound_menu_next = self.player.next
        self.sound_menu._sound_menu_previous = self.player.previous
        self.sound_menu._sound_menu_play = self.player.toggle
        self.sound_menu._sound_menu_pause = self.player.toggle
        self.sound_menu._sound_menu_is_playing = lambda: self.player.playing
    
        self.gui = UserInterface(self)
        self.sound_menu._sound_menu_raise = self.gui.window.present
        
        self._restore()
        
        self.player.connect("song-played", self._on_song_played)
        self.config.connect("changed::music-folder", self._set_new_playlist)
        self.config.connect("changed::is-browser", self._set_new_playlist)
        self.player.connect("song-changed", self._now_playing)
        self.player.connect("song-changed", self._update_pos)
        self.player.connect("toggled", self._toggled)
        
        indexer.connect("update-complete", self._on_index_updated)
        
        index_dirs = [os.path.expanduser("~")]
        
        if not self.config["music-folder"].startswith(index_dirs[0]):
            index_dirs += [self.config["music-folder"]]
        
        indexer.update(index_dirs)
    
    def _toggled(self, caller, playing):
        if playing:
            self.sound_menu.signal_playing()
        else:
            self.sound_menu.signal_paused()
    
    def on_uri_drop(self, model, uris, before=None, after=None):     
        paths = []
        
        for uri in uris:
            path = urllib.parse.unquote(uri[7:])
            
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for f in files:
                        if f.lower().endswith(KNOWN_EXTS):
                            path = os.path.join(root, f)
                            paths.append(path)
            else:
                paths.append(path)
        
        try:
            songs = [self._song_from_path(p) for p in paths]
        except KeyError:
            # FIXME
            # at least one of the songs is not in the library
            sys.stderr.write("song not found\n")
            return
        
        if before is not None:
            model.insert_before(before, songs)
        elif after is not None:
            model.insert_after(after, songs)
        else:
            model.append(songs)
    
    def song_selected(self, view, path, column):
        self.player.playlist.set(view._model)
        self.player.goto_pos(path[0])

    def _song_from_path(self, path):
        return Song(self.library.get_metadata(path))

    def _update_pos(self, player, *args):                
        if player.playlist.current is self.main_list:
            self.config["pos"] = self.main_list.pos

    def _on_index_updated(self, caller, was_updated):        
        if was_updated:
            GObject.idle_add(self._refresh_playlist)

    def _restore(self):
        self._refresh_playlist()
 
        if self.config["order-by"] == "shuffle":
            self.main_list.order_by("shuffle")

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
        action["Next"] = self.player.__next__
        
        action[key]()
    
    def _set_new_playlist(self, *args):        
        self._refresh_playlist()
        
        if self.config["order-by"] == "shuffle":
            self.main_list.order_by("shuffle")
        
        self.main_list.pos = 0
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
        GObject.idle_add(self.library.increment_played, song.uri)
        song["playcount"] += 1

        nm_connected = self._nm_props.Get("org.freedesktop.NetworkManager", "State") == NM_STATE_CONNECTED

        if self.scrobbler.is_connected() and nm_connected:
            self.scrobbler.submit(song["artist"], song["title"], int(time.time()), album=song["album"], length=song["duration"])
        else:
            sys.stderr.write("scrobbler: song {0} discarded\n nm_connected: {1}\n".format(song["title"], nm_connected))
                

    def _now_playing(self, player, song):
        self.sound_menu.song_changed(song["artist"],song["album"],song["title"])
        self.sound_menu.signal_playing()
        
        if not self.gui.window.is_active():
            self.gui.show_notification(song)

        nm_connected = self._nm_props.Get("org.freedesktop.NetworkManager", "State") == NM_STATE_CONNECTED

        if self.scrobbler.is_connected() and nm_connected:
            self.scrobbler.now_playing(song["artist"], song["title"], song["album"])
        else:
            sys.stderr.write("now playing: song {0} discarded\n nm_connected: {1}\n".format(song["title"], nm_connected))
    
    def order_changed(self, combo, model):        
        order = self.ORDER_MAPPING[combo.get_active()]      
        model.order_by(order)
        
        if model.backend is None:
            # save changes for library
            self.config["order-by"] = order
            self.config["pos"] = model.pos
    
    def start(self):
        if not self._already_running:
            Gtk.main()
        
    def quit(self, *args):
        if self.player.playing:
            self.gui.window.iconify()
            return True
        
        # submit to last.fm
        if self.scrobbler.is_connected():
            try:
                self.scrobbler.flush()
            except urllib.error.URLError as e:
                sys.stderr.write("lastfm.submit: %s\n" % e)
        
        Gtk.main_quit()