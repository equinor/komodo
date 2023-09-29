"""the matrix package capture the social conventions baked into the komodo
release matrix system. It should allow other parts of komodo to be capable of
handling an arbitrary large and funky matrix, without having to guess and/or
repeat itself.
"""
import itertools
import re
from typing import Iterator, Sequence, Tuple


def get_matrix(
    rhel_versions: Sequence[str],
    py_versions: Sequence[str],
) -> Iterator[Tuple[str, str]]:
    """Return tuples of rhel version and Python version, representing the
    current release matrix.
    """
    for product in itertools.product(rhel_versions, py_versions):
        rh_ver, py_ver = product
        yield (f"rhel{rh_ver}", f"py{str(py_ver).replace('.', '')}")


def format_release(base: str, rhel_ver: str, py_ver: str) -> str:
    """Format a base (e.g. a matrix file without the .yml suffix) such that it
    looks like a concrete release.
    """
    return f"{base}-{py_ver}-{rhel_ver}"


def get_matrix_base(release_name: str) -> str:
    """Return the base (e.g. matrix part of a concrete release). Should be the
    inverse of format_release for actual, concrete matrix releases.
    Hard-coded the suffix pattern '-py..-rhel.' or '-py...-rhel.'.
    """
    suffix = format_release("", "rhel[0-9]", r"py\d{2,3}")
    if re.search(suffix, release_name):
        return re.split(suffix, release_name)[0]
    # no matrix suffix at all
    return release_name
