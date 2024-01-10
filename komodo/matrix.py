"""the matrix package capture the social conventions baked into the komodo
release matrix system. It should allow other parts of komodo to be capable of
handling an arbitrary large and funky matrix, without having to guess and/or
repeat itself.
"""
import re
from typing import Iterable, Sequence


def get_matrix(
    py_versions: Sequence[str],
) -> Iterable[str]:
    """Return tuples of rhel version and Python version, representing the
    current release matrix.
    """
    for py_ver in py_versions:
        yield f"py{str(py_ver).replace('.', '')}"


def format_release(base: str, py_ver: str) -> str:
    """Format a base (e.g. a matrix file without the .yml suffix) such that it
    looks like a concrete release.
    """
    return f"{base}-{py_ver}"


def get_matrix_base(release_name: str) -> str:
    """Return the base (e.g. matrix part of a concrete release). Should be the
    inverse of format_release for actual, concrete matrix releases.
    Hard-coded the suffix pattern '-py..-rhel.' or '-py...-rhel.'.
    """
    suffix = format_release("", r"py\d{2,3}")
    if re.search(suffix, release_name):
        return re.split(suffix, release_name)[0]
    # no matrix suffix at all
    return release_name
