#!/usr/bin/env python

import locale
import __builtin__

from gi.repository import GObject

import youamp.controller

from youamp import DATA_DIR, GETTEXT_DOMAIN

# use locale instead of gettext, so GTK gets the change
#locale.bindtextdomain(GETTEXT_DOMAIN, DATA_DIR+"locale/")
locale.textdomain(GETTEXT_DOMAIN)
__builtin__.__dict__['_'] = locale.gettext

def main():
    GObject.threads_init()

    player = youamp.controller.Controller()
    player.start()

if __name__ == "__main__":
    main()
