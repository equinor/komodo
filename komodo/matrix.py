"""the matrix package capture the social conventions baked into the komodo
release matrix system. It should allow other parts of komodo to be capable of
handling an arbitrary large and funky matrix, without having to guess and/or
repeat itself.
"""

import itertools
import re
from typing import Dict, Iterator, Optional, Sequence, Tuple


def get_matrix(
    rhel_versions: Sequence[str],
    py_versions: Sequence[str],
    custom_coordinate: Optional[Dict[str, Sequence[str]]] = None,
) -> Iterator[Tuple[str, str, str]]:
    """Return tuples of rhel version, Python version and a single optional custom_coordinate,
    representing the current release matrix.
    """
    component_name = ""
    component_seq = [None]

    if custom_coordinate:
        if len(custom_coordinate) != 1:
            raise ValueError("custom_coordinate must contain exactly one item")
        component_name, component_seq = next(iter(custom_coordinate.items()))

    for product in itertools.product(rhel_versions, py_versions, component_seq):
        rh_ver, py_ver, other_ver = product
        rhel_tag, py_tag, other_tag = (
            f"rhel{rh_ver}",
            f"py{str(py_ver).replace('.', '')}",
            f"{component_name}{other_ver}" if other_ver else None,
        )

        yield rhel_tag, py_tag, other_tag


def format_release(
    base: str, rhel_ver: str, py_ver: str, other_component: Optional[str] = None
) -> str:
    """Format a base (e.g. a matrix file without the .yml suffix) such that it
    looks like a concrete release.
    """
    return (
        f"{base}-{py_ver}-{rhel_ver}-{other_component}"
        if other_component
        else f"{base}-{py_ver}-{rhel_ver}"
    )


def get_matrix_base(release_name: str) -> str:
    """Return the base (e.g. matrix part of a concrete release).
    Match release name on -py[nno]-rhel[n] and delimit using that
    """
    if re.search(r"-py\d{2,3}-rhel[0-9]", release_name):
        return release_name.split("-py")[0]
    return release_name
