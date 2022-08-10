"""the matrix package capture the social conventions baked into the komodo
release matrix system. It should allow other parts of komodo to be capable of
handling an arbitrary large and funky matrix, without having to guess and/or
repeat itself."""
import itertools

RH_VERSIONS = ["7"]
PY_VERSIONS = ["3.8"]


def get_matrix():
    """Return tuples of RHEL version and Python version, representing the
    current release matrix."""
    for product in itertools.product(RH_VERSIONS, PY_VERSIONS):
        rh_ver, py_ver = product
        yield ("rhel{}".format(rh_ver), "py{}".format(py_ver.replace(".", "")))


def format_release(base, rhel_ver, py_ver):
    """Format a base (e.g. a matrix file without the .yml suffix) such that it
    looks like a concrete release."""
    return "{}-{}-{}".format(base, py_ver, rhel_ver)


def get_matrix_base(release):
    """Return the base (e.g. matrix part of a concrete release). Should be the
    inverse of format_release for actual, concrete matrix releases."""
    for rhel_ver, py_ver in get_matrix():
        suffix = format_release("", rhel_ver, py_ver)
        if release.endswith(suffix):
            return release.split(suffix, 1)[0]
    # no matrix suffix at all
    return release
