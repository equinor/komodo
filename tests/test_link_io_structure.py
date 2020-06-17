from komodo.symlink.sanity_check import (
    read_link_structure,
    equal_links,
    assert_root_nodes,
    verify_integrity,
    sanity_main,
)
from komodo.symlink.create_links import create_symlinks, symlink_main

import os
import sys
import shutil
import json
import pytest
from tests import _get_test_root


def test_read_folder_structure(tmpdir):
    with tmpdir.as_cwd():
        os.mkdir("2012.01.rc1")
        os.mkdir("2012.01.rc2")
        os.mkdir("bleeding")
        os.mkdir("2012.01.12")

        os.symlink("2012.01.12", "2012.01")
        os.symlink("2012.01", "stable")
        os.symlink("2012.01", "testing")
        os.symlink("2012.01.rc2", "unstable")

        expected_result = {
            "root_folder": tmpdir,
            "root_links": ["stable", "unstable", "testing"],
            "links": {
                "2012.01": "2012.01.12",
                "stable": "2012.01",
                "testing": "2012.01",
                "unstable": "2012.01.rc2",
            },
        }

        output_dict = read_link_structure(os.getcwd())

        assert type(output_dict) == dict
        assert equal_links(output_dict, expected_result)


def test_create_symlinks(tmpdir):
    links_dict = {
        "root_folder": tmpdir,
        "links": {
            "2012.01": "2012.01.12",
            "stable": "2012.01",
            "testing": "2012.01",
            "unstable": "2012.01.rc2",
        },
    }

    with tmpdir.as_cwd():
        os.mkdir("2012.01.12")
        os.mkdir("2012.01.rc2")
        create_symlinks(links_dict)

        assert os.path.exists("stable")
        assert os.path.islink("stable")
        assert os.readlink("stable") == "2012.01"
        assert os.path.realpath("stable") == os.path.realpath("2012.01.12")
        assert os.path.realpath("unstable") == os.path.realpath("2012.01.rc2")


def test_integration(tmpdir):

    test_folder = _get_test_root()
    shutil.copy(os.path.join(test_folder, "data/links.json"), tmpdir)
    with tmpdir.as_cwd():
        with open("links.json") as link_file:
            input_dict = json.load(link_file)

        input_dict["root_folder"] = os.path.realpath(input_dict["root_folder"])

        os.mkdir(input_dict["root_folder"])
        os.mkdir(os.path.join(input_dict["root_folder"], "2012.01.12"))
        os.mkdir(os.path.join(input_dict["root_folder"], "2012.01.rc1"))

        create_symlinks(input_dict)

        output = read_link_structure(input_dict["root_folder"])
        assert equal_links(input_dict, output)


def test_root_links(tmpdir):

    test_folder = _get_test_root()
    shutil.copy(os.path.join(test_folder, "data/links.json"), tmpdir)
    with tmpdir.as_cwd():
        with open("links.json") as link_file:
            input_dict = json.load(link_file)

        assert_root_nodes(input_dict)

        input_dict["root_links"].append("non_exisiting")

        with pytest.raises(AssertionError):
            assert_root_nodes(input_dict)


def test_link_integrity(tmpdir):
    with tmpdir.as_cwd():
        os.mkdir("2012.01.rc2")
        os.mkdir("2012.01.12")

        test_dict = {
            "root_folder": tmpdir,
            "root_links": ["stable", "unstable", "testing"],
            "links": {
                "2012.01": "2012.01.12",
                "stable": "2012.01",
                "testing": "2012.01",
                "unstable": "2012.01.rc2",
            },
        }

        errors = verify_integrity(test_dict)
        assert errors == []

        test_dict["links"]["bleeding"] = "bleeding_py3"
        errors = verify_integrity(test_dict)
        assert errors == ["bleeding_py3 does not exist"]

        test_dict["links"]["2012.01.rc2"] = "unstable"
        errors = verify_integrity(test_dict)
        assert "2012.01.rc2 is part of a cyclic symlink" in errors
        assert "unstable is part of a cyclic symlink" in errors


def test_root_folder_error(tmpdir):
    with tmpdir.as_cwd():
        os.mkdir("2012.01.12")

        test_dict = {
            "root_folder": os.path.join(str(tmpdir), "non_existing"),
            "root_links": ["stable", "unstable", "testing"],
            "links": {
                "2012.01": "2012.01.12",
                "stable": "2012.01",
                "testing": "2012.01",
                "unstable": "2012.01.rc2",
            },
        }

        with pytest.raises(ValueError) as e:
            create_symlinks(test_dict)
        assert "does not exist" in str(e.value)

        test_dict["root_folder"] = os.path.relpath(str(tmpdir))
        with pytest.raises(ValueError) as e:
            create_symlinks(test_dict)
        assert "is not absolute" in str(e.value)


def test_link_error(tmpdir):
    with tmpdir.as_cwd():
        os.mkdir("2012.01.12")

        test_dict = {
            "root_folder": tmpdir,
            "root_links": ["stable", "unstable", "testing"],
            "links": {
                "2012.01": "2012.01.12",
                "stable": "2012.01",
                "testing": "2012.01",
                "unstable": "2012.01.rc2",
            },
        }
        with pytest.raises(ValueError) as e:
            create_symlinks(test_dict)
        assert "2012.01.rc2 does not exist" == str(e.value)


def test_root_link_error(tmpdir):
    with tmpdir.as_cwd():
        os.mkdir("2012.01.12")

        test_dict = {
            "root_folder": tmpdir,
            "root_links": ["stable", "unstable", "testing"],
            "links": {
                "2012.01": "2012.01.12",
                "stable": "2012.01",
                "unstable": "2012.01.rc2",
            },
        }
        with pytest.raises(ValueError) as e:
            create_symlinks(test_dict)
        assert "2012.01.rc2 does not exist" == str(e.value)


def test_executables(tmpdir):
    old_argv = sys.argv.copy()
    sys.argv = ["run", "links_test.json"]
    try:
        test_folder = _get_test_root()
        with open(os.path.join(test_folder, "data/links_full.json")) as input_file:
            input_data = json.load(input_file)

        with tmpdir.as_cwd():
            input_data["root_folder"] = str(tmpdir)
            with open("links_test.json", "w") as test_file:
                test_file.write(json.dumps(input_data))

            with pytest.raises(SystemExit):
                symlink_main()

            os.mkdir("bleeding-py36")
            os.mkdir("bleeding-py27")
            os.mkdir("2020.01.a0-py36")
            os.mkdir("2020.01.a0-py27")
            os.mkdir("2019.12.00-py36")
            os.mkdir("2019.12.00-py27")

            symlink_main()

            sanity_main()
    finally:
        sys.argv = old_argv
