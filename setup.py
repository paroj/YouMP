#!/usr/bin/env python

from distutils.core import setup
from DistUtilsExtra.command import *
from youamp import VERSION

setup(
      cmdclass = {"build": build_extra.build_extra,
                  "build_i18n":  build_i18n.build_i18n},
      name = "youamp",
      version = VERSION,
      description = "a lightweight music player",
      author = "Pavel Rojtberg",
      author_email = "pavel@rojtberg.net",
      url = "http://www.rojtberg.net/workspace/youamp/",
      license = "GNU GPL v3",
      long_description = """\
YouAmp places the focus on playback features instead of fancy graphics. 
It features itelligent replaygain selection and last.fm submission support.""",
      scripts = ["youamp-player"],
      packages = ["youamp", "youamp.ui"],
      data_files = [("share/icons/hicolor/scalable/apps/", ["data/youamp.svg"]),
                    ("share/applications/", ["youamp.desktop"]),
                    ("share/youamp/", ["data/interface.ui"])])
