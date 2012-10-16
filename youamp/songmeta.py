# coding: utf-8
from gi.repository import GObject, Gdk, GdkPixbuf

import urllib

from xml.etree.ElementTree import parse,dump

import os.path
import fnmatch

from youamp.indexer import media_art_identifier

import threading

# the API KEY is specific to this player
# please get an own at: http://www.last.fm/api/account
API_KEY = "2a7381c68a7b50cde9d9befac535c395"
REQ_URL = "http://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key={0}&artist={1}&album={2}"

def download_file(source, dest):
    req = urllib.request.urlopen(source)
    open(dest, "wb").write(req.read())

class SongMetaLastFM(GObject.GObject):
    __gsignals__ = {"new-cover": (GObject.SignalFlags.RUN_LAST, None, (str, str))}
    
    def __init__(self):
        GObject.GObject.__init__(self)
        
        self._downloader_th = None
    
    def _image_in_dir(self, song):
        """
        search for an image in the same directory as the music file
        """    
        dir = os.path.dirname(song.uri)
        
        try:
            img = fnmatch.filter(os.listdir(dir), "*.jpg")[0]
        except IndexError:
            return None
        
        return os.path.join(dir, img)

    def get_cover_path(self, song):
        if not song.display_cover:
            return None
        
        # use the image in song directory
        path = self._image_in_dir(song)
        
        if path is not None:
            return path
        
        # no image in song directory
        # try to look in media-art dir
        path = media_art_identifier(song)
        
        if os.path.exists(path):
            return path
                
        if self._downloader_th is not None:
            self._downloader_th.join(0)
        
        self._downloader_th = threading.Thread(target=self._downloader, args=(song, path))
        self._downloader_th.start()
        
        return None
        
    def _downloader(self, song, path):
        # try to download image
        uris = self._search_cover(str(song["artist"]), str(song["album"]))
        
        if uris[0] is None:
            # no cover found at requested resolution
            return
        
        download_file(uris[0], path)
        
        # rescale to 300px
        pb = GdkPixbuf.Pixbuf.new_from_file_at_size(path, 300, 300)  
        pb.savev(path, "jpeg", [], [])
        
        self.emit("new-cover", path, song["album"])

    def _search_cover(self, artist, title):
        req = REQ_URL.format(API_KEY, urllib.parse.quote(artist), urllib.parse.quote(title))
        
        try:
            resp = urllib.request.urlopen(req)
        except urllib.error.HTTPError:
            return []
        
        resp = parse(resp)
        return [e.text for e in resp.findall("album/image") if e.get("size") == "extralarge"]