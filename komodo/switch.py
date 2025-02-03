import os
import re
import shutil

from jinja2 import Template

from komodo.data import Data


def create_activator_switch(data: Data, prefix: str, release: str):
    """Given a prefix and a release, create an activator switch which
    will vary the selected activator based on the RHEL version and python version.
    """
    try:
        release_parts = release.split("-")
        release_python = None
        release_rhel = None

        for rhel_ver in release_parts:
            if re.match(r"rhel\d+", rhel_ver.strip()):
                release_rhel = rhel_ver.strip()
                break

        if not release_rhel:
            raise ValueError(f"Missing rhel version in release name: {release}")

        for py_ver in release_parts:
            if re.match(r"^py\d+", py_ver.strip()):
                release_python = py_ver.strip()
                break

        if not release_python:
            raise ValueError(f"Missing python version in release name: {release}")

        release_version = release_parts[0].strip() + "-" + release_python

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
                    py_version=release_python,
                    rhel_version=release_rhel,
                    prefix=prefix,
                    release=release_version,
                ),
            )
