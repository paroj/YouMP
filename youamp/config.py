from gi.repository import GConf

class Config(GConf.Client):
    """A dictonary like proxy for GConf.Client""" 
    
    def __init__(self, base_path):
        """@param base_path: the base path for further use"""
        GConf.Client.__init__(self)
        self._base_path = base_path
        self.add_dir(base_path[0:-1], GConf.ClientPreloadType.PRELOAD_RECURSIVE)
                 
    def notify_add(self, k, f):
        return GConf.Client.notify_add(self, self._base_path + k, f)

    def notify(self, k):
        GConf.Client.notify(self, self._base_path + k)
    
    def __contains__(self, k):
        return self.get(self._base_path + k) is not None
        
    def __getitem__(self, k):
        try:
            return self.get_value(self._base_path + k)
        except ValueError:
            return None
    
    def __setitem__(self, k, v):
        """
        @param k: key
        @param v: value. None for unsetting the key
        """
        if v is None:
            self.unset(self._base_path + k)
        elif isinstance(v, list):
            self.set_list(self._base_path+k, GConf.ValueType.STRING, [str(e) for e in v])
        else:
            self.set_value(self._base_path + k, v)
