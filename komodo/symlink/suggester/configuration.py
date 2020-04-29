import json

from komodo.symlink.suggester.release import Release


class Configuration(object):
    def __init__(self, conf):
        self.conf = conf
        self.links = conf["links"]

    def _month_alias_update_only(self, link, release):
        return self.links.get(link, None) == release.month_alias()

    def _get_concrete_release(self, link):
        release = Release(self.links[link])
        while not release.is_concrete():
            release = Release(self.links[repr(release)])
        return release

    def update(self, release, mode):
        link = "{}-{}".format(mode, release.py_ver())
        link_exists = link in self.links
        linked_release = self._get_concrete_release(link) if link_exists else None

        if mode == "unstable":
            if not linked_release or release.monthly_diff(linked_release) >= 0:
                self.links[link] = repr(release)

        elif mode == "testing":
            stable_link = "stable-{}".format(release.py_ver())
            stable = (
                self._get_concrete_release(stable_link)
                if stable_link in self.links
                else None
            )
            linked = self.links.get(link, None)

            # ripe is when stable is -1 month ago, ours is that the handle
            # already points to a release in the same month
            # if no stable, then it is ripe
            handle_ripe = stable.monthly_diff(release) == -1 if stable else True
            handle_ours = link_exists and linked_release.monthly_diff(release) == 0
            if handle_ripe or handle_ours:

                # i.e. if the linked release is a month alias
                if linked and not Release(linked).is_concrete():
                    self.links[release.month_alias()] = repr(release)
                    self.links[link] = release.month_alias()
                else:
                    self.links[link] = repr(release)
        elif mode == "stable":
            # Add/update deprecated link iff stable exists and has changed
            if self.links.get(link) != release.month_alias():
                dlink = link.replace("stable", "deprecated")
                self.links[dlink] = self.links[link]

            self.links[release.month_alias()] = repr(release)
            self.links[link] = release.month_alias()
        else:
            raise ValueError("mode {} was not recognized".format(mode))

    def to_json(self, json_kwargs):
        return json.dumps(self.conf, **json_kwargs)

    @staticmethod
    def from_json(conf_json_str):
        return Configuration(json.loads(conf_json_str))


def update(symlink_configuration, release_id, mode):
    """Return a touple of a string representing the new symlink config json,
    and whether or not an update was made. This function assumes the release_id
    is in the yyyy.mm.[part ...]-py[\\d+] format and that symlink_configuration
    is a string representing the current symlink config json."""
    json_kwargs = {"sort_keys": True, "indent": 4, "separators": (",", ": ")}
    release = Release(release_id)

    configuration = Configuration.from_json(symlink_configuration)
    configuration.update(release, mode)
    new_json_str = configuration.to_json(json_kwargs)

    old_json_str = json.dumps(json.loads(symlink_configuration), **json_kwargs)

    return "{}\n".format(new_json_str), new_json_str != old_json_str
