#!/usr/bin/env python3

import gettext

from gi.repository import GObject
import youamp.controller

gettext.install("youamp")

def main():
    GObject.threads_init()

    player = youamp.controller.Controller()
    player.start()

if __name__ == "__main__":
    main()
