import ctypes

_clib = ctypes.cdll.LoadLibrary("libtag_c.so.0")

_clib.taglib_tag_album.restype = ctypes.c_char_p
_clib.taglib_tag_artist.restype = ctypes.c_char_p
_clib.taglib_tag_title.restype = ctypes.c_char_p
_clib.taglib_tag_album.argtypes = [ctypes.c_void_p]
_clib.taglib_tag_title.argtypes = [ctypes.c_void_p]
_clib.taglib_tag_artist.argtypes = [ctypes.c_void_p]
_clib.taglib_tag_track.argtypes = [ctypes.c_void_p]
_clib.taglib_file_is_valid.restype = ctypes.c_bool
_clib.taglib_file_new.argtypes = [ctypes.c_char_p]
_clib.taglib_file_new.restype = ctypes.c_void_p
_clib.taglib_file_is_valid.argtypes = [ctypes.c_void_p]
_clib.taglib_file_tag.argtypes = [ctypes.c_void_p]
_clib.taglib_file_tag.restype = ctypes.c_void_p
_clib.taglib_file_free.argtypes = [ctypes.c_void_p]


class FileRef:
    def __init__(self, path):
        self._f = _clib.taglib_file_new(path.encode("utf-8"))

        if self._f == 0 or not _clib.taglib_file_is_valid(self._f):
            raise ValueError("Error")
            
        self._tag = _clib.taglib_file_tag(self._f)
    
    @property
    def artist(self):
        return _clib.taglib_tag_artist(self._tag).decode("utf-8")
    
    @property
    def album(self):
        return _clib.taglib_tag_album(self._tag).decode("utf-8")
    
    @property
    def title(self):
        return _clib.taglib_tag_title(self._tag).decode("utf-8")
    
    @property
    def track(self):
        return _clib.taglib_tag_track(self._tag)
    
    def __del__(self):
        _clib.taglib_tag_free_strings()
        _clib.taglib_file_free(self._f)