import os
import re
import subprocess
import sys

LATEST_PACKAGE_ALIAS = "*"
_PYPI_LATEST_VERSION_RE = r".+from\ versions\:\ (.+)\)"
# This command is deprecated. Hopefully it is not removed until a replacement
# is made. For updates on this, see https://github.com/pypa/pip/issues/9139
_PYPI_LATEST_VERSION_CMD = "python -m pip install --use-deprecated=legacy-resolver {}=="


def strip_version(version):
    """
    In order to be able to support both py2 and py3 we need to be able
    to have multiple versions of the same package/version due to
    differences in dependencies. This is achieved by adding i.e '+py3'
    to a version-spec in both the release and repository file. This func
    strips the '+' and everything behind for all pip packages so we are
    able to install.
    """
    return version.split("+")[0]


def latest_pypi_version(package):
    cmd = _PYPI_LATEST_VERSION_CMD.format(package)
    try:
        subprocess.check_output(cmd.split(" "), stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(sys.getfilesystemencoding())
        matches = re.match(_PYPI_LATEST_VERSION_RE, stderr)
        if matches.lastindex == 0:
            raise ValueError(
                f"got unexpected output from {cmd} using {_PYPI_LATEST_VERSION_RE}: {stderr}"
            )
        versions = matches.group(1).split(",")
        version = versions[len(versions) - 1].strip()
        if version == "none":
            return None
        return version
    raise ValueError(f"{cmd} did not raise CalledProcessError")


def get_git_revision_hash(path):
    env = os.environ.copy()
    env["GIT_DIR"] = f"{path}/.git"
    return (
        subprocess.check_output(["git", "rev-parse", "HEAD"], env=env)
        .decode(sys.getfilesystemencoding())
        .strip()
    )
