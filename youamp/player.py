import sys
import gst
import gobject

from gobject import GObject
from youamp import MAX_VOL

class Player(GObject):
    """
    A Playlist based player
    
    signals:
    song-changed: the song has changed
    song-played: the song was played
    tags-updated: the tags changed
    seek-chaned: the seek changed
    toggled: player was toggled
    """
    __gsignals__ = {"song-changed": (gobject.SIGNAL_RUN_LAST, None, (object,)),
                    "song-played": (gobject.SIGNAL_RUN_LAST, None, (object,)),
                    "tags-updated": (gobject.SIGNAL_RUN_LAST, None, (object,)),
                    "seek-changed": (gobject.SIGNAL_RUN_LAST, None, (float,)),
                    "toggled": (gobject.SIGNAL_RUN_LAST, None, (bool,))}
                                   
    def __init__(self, config):
        GObject.__init__(self)
        self.playing = False
        self.playlist = None
        self._current = None
        self._seek_emit_id = None
        self._set_duration_id = None
        self._config = config

        self._player = gst.element_factory_make("playbin2")
        
        rg_bin = """audioconvert ! rgvolume name="rgvolume" ! rglimiter ! 
                    audioconvert ! audioresample ! autoaudiosink"""#pulsesink name="sink" """
        
        rg_bin = gst.parse_bin_from_description(rg_bin, True)
        
        self._player.set_property("audio-sink", rg_bin)
        self._rgvolume = rg_bin.get_by_name("rgvolume")
        
        # self._sink = rg_bin.get_by_name("sink")
        
        self._apply_rg_settings()
        
        bus = self._player.get_bus()
        bus.add_signal_watch()

        # set up signal handlers
        bus.connect("message::eos", self.next)
        bus.connect("message::error", self._on_error)
        bus.connect("message::state-changed", self._on_state_changed)
        bus.connect("message::tag", self._on_tag)

        if config["gapless"]:
            self._player.connect("about-to-finish", self._gapless)
     
        self._config.notify_add("volume", self._set_volume)
        self._config.notify_add("rg-preamp", lambda *args: self._apply_rg_settings())
        self._config.notify_add("no-rg-preamp", lambda *args: self._apply_rg_settings())

    def _gapless(self, player):
        self.next(play=False)
        player.set_property("uri", "file://"+self._current.uri)

    def next(self, play=True, *args):
        if self.playlist.jump_to is not None:
            self.goto_pos(self.playlist.jump_index(), play)
            self.playlist.jump_to = None
        else:
            self.goto_pos(self.playlist.next_song(self._current), play)

    def tracks(self):
        return len(self.playlist)

    def goto_pos(self, pos, play=True):
        # emit song-played for previous track
        if self._current is not None:
            self._emit_played()
        
        pos %= len(self.playlist)
        self._current = self.playlist[pos]

        self.playlist.pos = pos
        
        if play: 
            self.start_playback()

    def previous(self):
        if self.get_time() > 3:
            self._emit_played()
            self.seek_to(0.0)
            return

        self.goto_pos(self.playlist.pos - 1)
    
    def get_time(self):
        """returns position in seconds"""
        try:
            s = self._player.query_position(gst.FORMAT_TIME)[0]/ gst.SECOND
            return s
        except gst.QueryError, e:
            sys.stderr.write("get_time: %s\n" % e)

    def get_seek(self):
        """returns position as fraction"""
        try:
            length = float(self._player.query_duration(gst.FORMAT_TIME)[0])
            return self._player.query_position(gst.FORMAT_TIME)[0]/length
        except gst.QueryError, e:
            sys.stderr.write("get_seek: %s\n" % e)
            return 0.0           

    def seek_to(self, pos):
        try:
            length = float(self._player.query_duration(gst.FORMAT_TIME)[0])
        except gst.QueryError, e:
            sys.stderr.write("seek_to: %s\n" % e)
        else:        
            self._player.seek_simple(gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH, int(length*pos))
    
    def _emit_played(self):
        self.emit("song-played", self._current)
            
    def load_track(self):
        if self._current is None:
            self._current = self.playlist[self.playlist.pos]
        
        self._player.set_state(gst.STATE_NULL)
        self._player.set_property("uri", "file://"+self._current.uri)
        self._player.set_state(gst.STATE_PAUSED)

    def _on_state_changed(self, bus, message):
        # wait for decodebin to move from ready to paused
        # up to there all tag events were fired
        if message.src.get_name().startswith("decodebin"):
            state = message.parse_state_changed()
            if state[0:2] == [gst.STATE_READY, gst.STATE_PAUSED]:
                self._rgvolume.set_property("album-mode", self._is_same_album())
                
                try:
                    self._current["duration"] = int(self._player.query_duration(gst.FORMAT_TIME)[0]/gst.SECOND)
                except gst.QueryError:
                    sys.stderr.write("could not set song length\n")
                    
                self.emit("song-changed", self._current)
  
    def start_playback(self):
        self.load_track()
        self._player.set_state(gst.STATE_PLAYING)
        
        if not self.playing:
            self._emit_seek_id = gobject.timeout_add_seconds(1, self._emit_seek)
            self.emit("toggled", True)

        self.playing = True

    def _on_error(self, bus, message):
        sys.stderr.write("Error: %s\n" % message.parse_error()[0])
        
    def __del__(self):
        self._player.set_state(gst.STATE_NULL)
        
    def _set_volume(self, client, cxn_id, entry, data):
        vol = min(1.0, max(0.0, entry.get_value().get_float()))

        self._player.set_property("volume", vol*MAX_VOL)       
		
    def toggle(self):
        if self.playing:
            self._player.set_state(gst.STATE_PAUSED)
            self.playing = False
            gobject.source_remove(self._emit_seek_id)
        else:
            self._player.set_state(gst.STATE_PLAYING)
            self.playing = True
            
            self._emit_seek_id = gobject.timeout_add_seconds(1, self._emit_seek)
        
        self.emit("toggled", self.playing)

    def has_rg_info(self):
        cur = self._current
        
        return "replaygain-track-gain" in cur or "replaygain-album-gain" in cur
    
    def _is_same_album(self):
        pos = self.playlist.pos
        length = self.tracks()
        cur = self._current
        prev = self.playlist[(pos - 1) % length]
        next = self.playlist[(pos + 1) % length]
    
        if cur["album"] == "None":
            return False
        else:
            return cur["album"] in (prev["album"], next["album"])
    
    def _apply_rg_settings(self):
        self._rgvolume.set_property("pre-amp", self._config["rg-preamp"])
        self._rgvolume.set_property("fallback-gain", self._config["no-rg-preamp"])

    def _emit_seek(self):
        # do not send update if we are already paused
        self.emit("seek-changed", self.get_seek())
        
        return True # if True will be called repeatedly
    
    def _on_tag(self, bus, message):
        self._update_song(message.parse_tag())
        self.emit("tags-updated", self._current)
        
    def _update_song(self, new_tags):        
        for key in new_tags.keys():
            v = new_tags[key]

            if key in ("artist", "album", "title"):
                continue # we get these tags from db, use those for consistency
            
            self._current[key] = v
