import os.path

class ValueBox:
    def __init__(self, val):
        self._val = val
        
    def get_value(self):
        return self
    
    def get_bool(self):
        return self._val
    
    def get_float(self):
        return self._val
    
    def get_string(self):
        return self._val

class ConfigFile(dict):
    def __init__(self):
        dict.__init__(self)
        self._path = os.path.expanduser("~/.config/youamp")   
        
        if not os.path.exists(self._path):
            f = open(self._path, "w")
            f.close()
        
        file = open(self._path)
        self._callbacks = dict()
        
        typemap = {"i": int, "f": float, "s": str, "b": lambda v: v == "True"}
        
        for l in file:
            k, v = l.split(" = ")
            v = v.strip()
            t, v = v.split(":", 1)
            v = typemap[t](v)
            self[k] = v
    
    def write(self):
        typemap = {int: "i", float: "f", str: "s", bool: "b"}
        file = open(self._path, "w")
        
        for k, v in self.iteritems():
            t = typemap[type(v)]
            file.write("%s = %s:%s\n" % (k, t, v))
        
        file.close()
    
    def notify_add(self, k, f):        
        self._callbacks[k].append(f)
    
    def notify(self, k):
        for f in self._callbacks[k]:
            f(None, None, ValueBox(self[k]), None)
    
    def __setitem__(self, k, v):
        if not self._callbacks.has_key(k):
            self._callbacks[k] = []

        old_v = self[k] if self.has_key(k) else None
        
        dict.__setitem__(self, k, v)

        if old_v != None and old_v != self[k]:
            self.notify(k)