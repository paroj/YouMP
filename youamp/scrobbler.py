"""
A pure-python library to assist sending data to AudioScrobbler (the LastFM backend)

original work by Michel Albert (http://exhuma.wicked.lu/projects/python/scrobbler/)
ruined by Pavel Rojtberg (http://www.rojtberg.net/)

License: LGPL v3
"""
import _thread
from time import mktime

from gi.repository import GObject
import threading

import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse

from datetime import timedelta, datetime
from hashlib import md5

"Forwards Audioscrobbler errors"
E_ASCROBBLER = 0

"Raised on general Protocol errors"
E_PROTOCOL = 1

class Scrobbler(GObject.GObject):
    __gsignals__ = {"error": (GObject.SignalFlags.RUN_LAST, None, (int, str))}

    def __init__(self):        
        GObject.GObject.__init__(self)
        self._session_id = None
        self._post_uri = None
        self._now_uri = None
        self._hard_fails = 0
        self._last_hs = None   # Last handshake time
        self._hs_delay = 0      # wait this many seconds until next handshake
        self._submit_cache = []
        self._max_cache = 5      # keep only this many songs in the cache
        self._protocol_version = '1.2'
        self._user = None
        self._pass = None
        self._client = None
        self._state = None

    def login(self, user, passwd, client=('tst', '1.0')):
        """Authencitate with AS (The Handshake)

        @param user:     The username
        @param passwd: md5-hash of the user-password
        @param client:   Client information (see http://www.audioscrobbler.net/development/protocol/ for more info)
        @type  client:   Tuple: (client-id, client-version)"""

        self._user = user
        self._pass = passwd
        self._client = client

        self._loginth = threading.Thread(target=self._login)
        self._loginth.start()
      
    def get_state(self):
        return self._state
    
    def is_connected(self):
        return self._state == "OK"
    
    def now_playing(self, artist, track, album="", length="", trackno="", mbid=""):
        """Tells audioscrobbler what is currently running in your player. This won't
           affect the user-profile on last.fm. To do submissions, use the "submit"
           method
        
           @param artist:  The artist name
           @param track:   The track name
           @param album:   The album name
           @param length:  The song length in seconds
           @param trackno: The track number
           @param mbid:    The MusicBrainz Track ID"""
        _thread.start_new_thread(self._now_playing,
                                (artist, track, album, length, trackno, mbid))

    def _login(self):    
        if self._last_hs is not None:
            next_allowed_hs = self._last_hs + timedelta(seconds=self._hs_delay)
            if datetime.now() < next_allowed_hs:
                delta = next_allowed_hs - datetime.now()
                self.emit("error", E_PROTOCOL, "Please wait another %d seconds until next handshake (login) attempt." % delta.seconds)
                return
    
        self._last_hs = datetime.now()
    
        tstamp = int(mktime(datetime.now().timetuple()))
        url = "http://post.audioscrobbler.com/"
        
        token = md5(("%s%d" % (self._pass, int(tstamp))).encode("utf-8")).hexdigest()
        values = {
            'hs': 'true',
            'p': self._protocol_version,
            'c': self._client[0],
            'v': self._client[1],
            'u': self._user,
            't': tstamp,
            'a': token
            }
       
        data = urllib.parse.urlencode(values)
        req = urllib.request.Request("%s?%s" % (url, data))
        response = urllib.request.urlopen(req)
        result = response.read()
        lines = result.decode().split('\n')
       
        if lines[0] in ("BADAUTH", "BANNED", "BADTIME"):
            self._state = lines[0]
            self.emit("error", E_ASCROBBLER, lines[0])
            return
    
        elif lines[0].startswith('FAILED'):
            self._handle_hard_error()
          
            self._state = lines[0]
            self.emit("error", E_ASCROBBLER, lines[0])
            return
    
        elif lines[0] == 'OK':
            # wooooooohooooooo. We made it!
            self._state = lines[0]
            self._session_id = lines[1]
            self._now_uri = lines[2]
            self._post_uri = lines[3]
            self._hard_fails = 0
        else:
            # some hard error
            self._handle_hard_error()

    def _handle_hard_error(self):
        "Handles hard errors."
        if self._hs_delay == 0:
            self._hs_delay = 60
        elif self._hs_delay < 120 * 60:
            self._hs_delay *= 2
        if self._hs_delay > 120 * 60:
            self._hs_delay = 120 * 60
    
        self._hard_fails += 1
       
        if self._hard_fails == 3:
            self._session_id = None
    
    def _now_playing(self, artist, track, album, length, trackno, mbid):       
        self._loginth.join()
       
        assert self._session_id is not None, "No session available"
        assert length == "" or isinstance(int, length), "length should be of type int"
        assert trackno == "" or isinstance(int, trackno), "trackno should be of type int"
    
        values = {'s': self._session_id,
            'a': artist,
            't': track,
            'b': album,
            'l': length,
            'n': trackno,
            'm': mbid}
    
        data = urllib.parse.urlencode(values)
        req = urllib.request.Request(self._now_uri, data.encode("utf-8"))

        try:
            response = urllib.request.urlopen(req)
        except urllib.error.URLError as e:
            self.emit("error", E_ASCROBBLER, e)
            return

        result = response.read()
    
        i = 0
        while result.strip() == "BADSESSION" and i < 5:
            # retry to login
            self._login()
    
            # retry to submit the data
            req = urllib.request.Request(self._now_uri, data)
            response = urllib.request.urlopen(req)
            result = response.read()
    
            if result.strip() == "OK":
                return
    
            i += 1
    
        # either we tried 5 times, or we still have a bad session
        if result.strip() == "BADSESSION":
            self.emit("error", E_ASCROBBLER, result)
        else:
            return

    def submit(self, artist, track, time, source='P', rating="", length="", album="",
               trackno="", mbid="", autoflush=False):
        """Append a song to the submission cache. Use 'flush()' to send the cache to
       AS. You can also set "autoflush" to True.
    
       From the Audioscrobbler protocol docs:
       ---------------------------------------------------------------------------
    
       The client should monitor the user's interaction with the music playing
       service to whatever extent the service allows. In order to qualify for
       submission all of the following criteria must be met:
    
       1. The track must be submitted once it has finished playing. Whether it has
          finished playing naturally or has been manually stopped by the user is
          irrelevant.
       2. The track must have been played for a duration of at least 240 seconds or
          half the track's total length, whichever comes first. Skipping or pausing
          the track is irrelevant as long as the appropriate amount has been played.
       3. The total playback time for the track must be more than 30 seconds. Do
          not submit tracks shorter than this.
       4. Unless the client has been specially configured, it should not attempt to
          interpret filename information to obtain metadata instead of tags (ID3,
          etc).
    
       @param artist: Artist name
       @param track:  Track name
       @param time:   Time the track *started* playing in the UTC timezone (see
                      datetime.utcnow()).
    
                      Example: int(time.mktime(datetime.utcnow()))
       @param source: Source of the track. One of:
                      'P': Chosen by the user
                      'R': Non-personalised broadcast (e.g. Shoutcast, BBC Radio 1)
                      'E': Personalised recommendation except Last.fm (e.g.
                           Pandora, Launchcast)
                      'L': Last.fm (any mode). In this case, the 5-digit Last.fm
                           recommendation key must be appended to this source ID to
                           prove the validity of the submission (for example,
                           "L1b48a").
                      'U': Source unknown
       @param rating: The rating of the song. One of:
                      'L': Love (on any mode if the user has manually loved the
                           track)
                      'B': Ban (only if source=L)
                      'S': Skip (only if source=L)
                      '':  Not applicable
       @param length: The song length in seconds
       @param album:  The album name
       @param trackno:The track number
       @param mbid:   MusicBrainz Track ID
       @param autoflush: Automatically flush the cache to AS?
       """    
        source = source.upper()
        rating = rating.upper()
    
        assert not (source == 'L' and (rating == 'B' or rating == 'S')), \
            "You can only use rating 'B' or 'S' on source 'L'"
    
        assert not (source == 'P' and length == ''), \
            "Song length must be specified when using 'P' as source"

        assert isinstance(time, int), "The time parameter must be a unix timestamp"
    
        self._submit_cache.append(
                                  {'a': str(artist).encode('utf-8'),
                                  't': str(track).encode('utf-8'),
                                  'i': time,
                                  'o': source,
                                  'r': rating,
                                  'l': length,
                                  'b': str(album).encode('utf-8'),
                                  'n': trackno,
                                  'm': mbid
                                  }
                                  )
    
        if autoflush or len(self._submit_cache) >= self._max_cache:
            _thread.start_new_thread(self.flush, ())

    def flush(self, inner_call=False):
        """Sends the cached songs to AS.
    
       @param inner_call: Internally used variable. Don't touch!"""       
        if len(self._submit_cache) == 0:
            return
       
        self._loginth.join()
       
        assert self._session_id is not None, "No session available"
    
        values = {}
    
        for i, item in enumerate(self._submit_cache):
            for key in item:
                values[key + "[%d]" % i] = item[key]
    
        values['s'] = self._session_id
    
        data = urllib.parse.urlencode(values)
        req = urllib.request.Request(self._post_uri, data)
        response = urllib.request.urlopen(req)
        result = response.read()
        lines = result.split('\n')
       
        if lines[0] == "OK":
            self._submit_cache = []
        elif lines[0] == "BADSESSION":
            if inner_call is False:
                self._login()
                self.flush(inner_call=True)
            else:
                print("Warning: infinite loop prevented")
                return
        elif lines[0].startswith('FAILED'):
            self._handle_hard_error()
          
            self.emit("error", E_ASCROBBLER, lines[0])
        else:
            # some hard error
            self._handle_hard_error()

