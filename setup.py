#!/usr/bin/env python

from distutils.core import setup
from DistUtilsExtra.command import *

import glob

DEST="/opt/extras.ubuntu.com/youamp/"

class my_build_i18n(build_i18n.build_i18n):
    def run(self):
        build_i18n.build_i18n.run(self)
        
        df = self.distribution.data_files
        
        self.distribution.data_files = [(d.replace("share/locale/", DEST+"locale/"), s) for d, s in df]

setup(
      cmdclass = {"build": build_extra.build_extra,
                  "build_i18n":  my_build_i18n},
      name = "youamp",
      version = "12.10",
      description = "a lightweight music player",
      author = "Pavel Rojtberg",
      author_email = "pavel@rojtberg.net",
      url = "http://www.rojtberg.net/",
      license = "GNU GPL v3",
      long_description = """\
YouAmp places the focus on playback features instead of fancy graphics. 
It features itelligent replaygain selection and last.fm submission support.""",
      data_files = [("share/applications/", ["data/youamp-player.desktop"]),
                    (DEST, ["data/interface.ui", "data/youamp.svg", "data/youamp.svg", "youamp-player.py"]),
                    (DEST+"youamp/", glob.glob("youamp/*.py")),
                    (DEST+"youamp/ui/", glob.glob("youamp/ui/*.py"))])
