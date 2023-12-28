from __future__ import annotations

import json
from typing import Any, MutableMapping, Tuple

from komodo.symlink.suggester.release import Release
from komodo.symlink.types import LinkDict


class Configuration:
    def __init__(self, conf: LinkDict) -> None:
        self.conf = conf
        self.links: MutableMapping[str, str] = conf["links"]  # type: ignore

    def _month_alias_update_only(self, link: str, release: Release) -> bool:
        return self.links.get(link, None) == release.month_alias()

    def _get_concrete_release(self, link: str) -> Release:
        release = Release(self.links[link])
        while not release.is_concrete():
            release = Release(self.links[repr(release)])
        return release

    def update(self, release: Release, mode: str) -> None:
        link = f"{mode}-{release.py_ver()}"
        link_exists = link in self.links
        linked_release = self._get_concrete_release(link) if link_exists else None

        if mode == "unstable":
            if not linked_release or release.monthly_diff(linked_release) >= 0:
                self.links[link] = repr(release)

        elif mode == "testing":
            stable_link = f"stable-{release.py_ver()}"
            stable = (
                self._get_concrete_release(stable_link)
                if stable_link in self.links
                else None
            )
            linked = self.links.get(link, None)

            # ripe is when stable is -1 month ago, ours is that the handle
            # already points to a release in the same month
            # if no stable, then it is ripe
            handle_ripe = stable.monthly_diff(release) <= -1 if stable else True
            assert linked_release is not None
            handle_ours = link_exists and linked_release.monthly_diff(release) == 0
            if handle_ripe or handle_ours:
                # i.e. if the linked release is a month alias
                if linked and not Release(linked).is_concrete():
                    self.links[release.month_alias()] = repr(release)
                    self.links[link] = release.month_alias()
                else:
                    self.links[link] = repr(release)
        elif mode == "stable":
            self.links[release.month_alias()] = repr(release)
            self.links[link] = release.month_alias()
        else:
            msg = f"Mode {mode} was not recognized"
            raise ValueError(msg)

    def to_json(self, json_kwargs: Any) -> str:
        return json.dumps(self.conf, **json_kwargs)

    @staticmethod
    def from_json(conf_json_str: bytes) -> Configuration:
        return Configuration(json.loads(conf_json_str))


def update(
    symlink_configuration: bytes, release_id: str, mode: str
) -> Tuple[str, bool]:
    """Return a tuple of a string representing the new symlink config json,
    and whether or not an update was made. This function assumes the release_id
    is in the yyyy.mm.[part ...]-py[\\d+] format and that symlink_configuration
    is a string representing the current symlink config json.
    """
    json_kwargs = {"sort_keys": True, "indent": 4, "separators": (",", ": ")}
    release = Release(release_id)

    configuration = Configuration.from_json(symlink_configuration)
    configuration.update(release, mode)

    new_json_str = configuration.to_json(json_kwargs)
    old_json_str = json.dumps(json.loads(symlink_configuration), **json_kwargs)  # type: ignore

    configuration_changed = new_json_str != old_json_str

    return f"{new_json_str}\n", configuration_changed
