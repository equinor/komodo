import os
import subprocess
import sys


def strip_version(version):
    """In order to be able to support both py2 and py3 we need to be able
    to have multiple versions of the same package/version due to
    differences in dependencies. This is achieved by adding i.e '+py3'
    to a version-spec in both the release and repository file. This func
    strips the '+' and everything behind for all pip packages so we are
    able to install.
    """
    return version.split("+")[0]


def get_git_revision_hash(path):
    env = os.environ.copy()
    env["GIT_DIR"] = f"{path}/.git"
    return (
        subprocess.check_output(["git", "rev-parse", "HEAD"], env=env)
        .decode(sys.getfilesystemencoding())
        .strip()
    )
