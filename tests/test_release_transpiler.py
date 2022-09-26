import os

import yaml

from komodo.release_transpiler import build_matrix_file, transpile_releases
from tests import _get_test_root, _load_yaml

builtins = {
    "lib1": {
        "rhel6": {"py27": "0.1.2", "py36": "1.2.3", "py38": "1.2.4"},
        "rhel7": {
            "py27": "0.1.2+builtin",
            "py36": "1.2.3+builtin",
            "py38": "1.2.3+builtin",
        },
    },
}


def test_build_release_matrix(tmpdir):
    release_base = "2020.01.a1"
    release_folder = os.path.join(_get_test_root(), "data/test_releases/")
    with tmpdir.as_cwd():
        build_matrix_file(release_base, release_folder, builtins)
        new_release_file = "{}.yml".format(release_base)
        assert os.path.isfile(new_release_file)
        with open(new_release_file) as f:
            release_matrix = yaml.safe_load(f)

        assert release_matrix["lib1"] == builtins["lib1"]
        assert "py27" not in release_matrix["lib2"]
        assert release_matrix["lib2"] == "2.3.4"


def test_transpile(tmpdir):
    release_file = os.path.join(_get_test_root(), "data", "test_release_matrix.yml")
    release_base = os.path.basename(release_file).strip(".yml")
    with tmpdir.as_cwd():
        transpile_releases(release_file, os.getcwd())
        for rhel_ver in ("rhel7",):
            for py_ver in ("py38",):
                assert os.path.isfile(
                    "{}-{}-{}.yml".format(release_base, py_ver, rhel_ver)
                )
