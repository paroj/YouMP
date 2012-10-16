from hashlib import md5

from youamp import VERSION

class Preferences:
    def __init__(self, *args):
        self._created = False
        self._args = args

    def cshow(self):
        if not self._created:
            self._create(*self._args)
            self._created = True

        self.w.show()

    def _create(self, config, scrobbler, xml):
        self.w = xml.get_object("preferences")
        xml.get_object("preferences_close").connect("clicked", lambda *args: self.w.hide_on_delete())

        self.config = config
        self._scrobbler = scrobbler
        self._scrobbler.connect("error", self._update_lfm_state)

        music_folder = xml.get_object("music_folder")
        music_folder.set_current_folder(self.config["music-folder"])
        music_folder.connect("current-folder-changed", self._on_mf_changed)

        rg_scale = xml.get_object("rg_preamp")
        rg_scale.set_value(self.config["rg-preamp"])
        rg_scale.connect("value-changed", self._on_rg_changed)

        no_rg_scale = xml.get_object("no_rg_preamp")
        no_rg_scale.set_value(self.config["no-rg-preamp"])
        no_rg_scale.connect("value-changed", self._on_no_rg_changed)

        user_entry = xml.get_object("lastfm_user")
        user_entry.set_text(self.config["lastfm-user"])
        user_entry.connect("focus-out-event", self._on_lfm_user_changed)

        pass_entry = xml.get_object("lastfm_pass")
        pass_entry.set_text("******" if self.config["lastfm-pass"] != "" else "")
        pass_entry.connect("focus-out-event", self._on_lfm_pass_changed)

        ss = scrobbler.get_state()

        if ss == "OK":
            state = _("Connected")
        elif ss == "BADAUTH":
            state = _("Wrong login data")
        else:
            state = _("Disconnected")

        self._lastfm_state = xml.get_object("lastfm_state")
        self._lastfm_state.set_text(state)

    def _update_lfm_state(self, caller, e, msg):
        if msg == "BADAUTH":
            state = _("Wrong login data")
        else:
            state = _("Disconnected")

        self._lastfm_state.set_text(state)

    def _try_login(self):
        self._scrobbler.login(self.config["lastfm-user"], self.config["lastfm-pass"], ("you", VERSION))
        self._lastfm_state.set_text(_("Connected"))

    def _on_lfm_user_changed(self, caller, ev):
        txt = caller.get_text()

        if self.config["lastfm-user"] == txt:
            return

        self.config["lastfm-user"] = txt
        self._try_login()

    def _on_lfm_pass_changed(self, caller, ev):
        txt = caller.get_text()

        if txt == "******":
            return

        self.config["lastfm-pass"] = md5(txt).hexdigest()
        self._try_login()

    def _on_mf_changed(self, caller):
        self.config["music-folder"] = caller.get_current_folder()

    def _on_rg_changed(self, caller):
        self.config["rg-preamp"] = caller.get_value()

    def _on_no_rg_changed(self, caller):
        self.config["no-rg-preamp"] = caller.get_value()
