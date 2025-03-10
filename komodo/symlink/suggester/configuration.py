import json
from typing import List, Tuple

from komodo.symlink.sanity_check import suggest_missing_roots
from komodo.symlink.suggester.release import Release


class Configuration:
    def __init__(self, conf) -> None:
        self.conf = conf
        self.links = conf["links"]
        self.root_links = conf.get("root_links", [])

    def _month_alias_update_only(self, link, release):
        return self.links.get(link, None) == release.month_alias()

    def _get_concrete_release(self, link):
        release = Release(self.links[link])
        while not release.is_concrete():
            release = Release(self.links[repr(release)])
        return release

    def update(self, release, mode, python_versions: List[str]):
        for _python_version in python_versions:
            python_version = _python_version.strip()
            release.set_python_version(python_version)

            link = f"{mode}-{python_version}"
            link_exists = link in self.links
            linked_release = self._get_concrete_release(link) if link_exists else None

            if mode == "testing":
                stable_link = f"stable-{python_version}"
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
                handle_ours = link_exists and linked_release.monthly_diff(release) == 0
                if handle_ripe or handle_ours:
                    # i.e. if the linked release is a month alias
                    if linked and not Release(linked).is_concrete():
                        self.links[release.month_alias()] = repr(release)
                        self.links[link] = release.month_alias()
                    else:
                        self.links[link] = repr(release)
            elif mode in {"stable", "deprecated"}:
                self.links[release.month_alias()] = repr(release)
                self.links[link] = release.month_alias()
            else:
                msg = f"Mode {mode} was not recognized"
                raise ValueError(msg)

    def to_json(self, json_kwargs):
        return json.dumps(self.conf, **json_kwargs)

    @staticmethod
    def from_json(conf_json_str):
        return Configuration(json.loads(conf_json_str))


def update(
    symlink_configuration, release_id, mode, python_versions: List[str] = None
) -> Tuple[str, bool]:
    """Return a tuple of a string representing the new symlink config json,
    and whether an update was made. This function assumes the release_id
    is in the yyyy.mm.[part ...] format and will look for python suffix (-py38, -py311)
    if no python_versions are passed. Symlink_configuration shall be a string
    representing the current symlink config json.
    """
    json_kwargs = {"sort_keys": True, "indent": 4, "separators": (",", ": ")}

    id_parts = release_id.split("-")
    release = Release(id_parts[0])
    if not python_versions:
        python_versions = [part for part in id_parts[1:] if "py" in part][:1]

    configuration = Configuration.from_json(symlink_configuration)
    configuration.update(release, mode, python_versions)
    new_json_str = configuration.to_json(json_kwargs)

    missing_roots = suggest_missing_roots(json.loads(new_json_str))
    if missing_roots:
        appended_roots = json.loads(new_json_str)

        for missing_root in missing_roots:
            if "root_links" in appended_roots:
                appended_roots["root_links"].append(missing_root)

        new_json_str = json.dumps(appended_roots, **json_kwargs)

    old_json_str = json.dumps(json.loads(symlink_configuration), **json_kwargs)
    configuration_changed = new_json_str != old_json_str

    return f"{new_json_str}\n", configuration_changed
