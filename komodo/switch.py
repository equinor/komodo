import os
import re
import shutil

from jinja2 import Template

from komodo.data import Data


def extract_versions(release_string: str) -> (str, str, str, str):
    release_parts = release_string.split("-")
    release_python = release_rhel = release_custom = ""

    for part in release_parts:
        if release_rhel and release_python:
            release_custom = part  # optional custom part is always last
            break
        if not release_rhel and re.match(r"rhel\d+", part.strip()):
            release_rhel = part.strip()
        if not release_python and re.match(r"^py\d+", part.strip()):
            release_python = part.strip()

    if not release_rhel:
        raise ValueError(f"Missing RHEL version in release name: {release_string}")
    if not release_python:
        raise ValueError(f"Missing Python version in release name: {release_string}")

    # Construct the release version string
    base_version = f"{release_string.split('-py')[0]}-{release_python}"
    return base_version, release_python, release_rhel, release_custom


def create_activator_switch(data: Data, prefix: str, release: str):
    """Given a prefix and a release, create an activator switch which
    will vary the selected activator based on the RHEL version and python version.
    """
    try:
        release_version, python_version, rhel_version, custom_version = (
            extract_versions(release_string=release)
        )
    except ValueError:
        # likely a build that does not require an activator switch
        return

    release_path = os.path.join(prefix, release_version)
    if os.path.exists(release_path):
        if os.path.islink(release_path):
            os.unlink(release_path)
        else:
            shutil.rmtree(release_path)

    os.makedirs(release_path)

    for template, enable_script in [
        ("activator_switch.tmpl", "enable"),
        ("activator_switch.csh.tmpl", "enable.csh"),
    ]:
        with open(
            os.path.join(release_path, enable_script), "w", encoding="utf-8"
        ) as activator, open(data.get(template), encoding="utf-8") as activator_tmpl:
            activator.write(
                Template(activator_tmpl.read(), keep_trailing_newline=True).render(
                    py_version=python_version,
                    rhel_version=rhel_version,
                    prefix=prefix,
                    release=release_version,
                    custom_version=custom_version,
                ),
            )
