import json
import os
import shutil
import sys

import pytest

from komodo.symlink.create_links import create_symlinks, symlink_main
from komodo.symlink.sanity_check import (
    _compare_dicts,
    _sort_lists_in_dicts,
    assert_root_nodes,
    equal_links,
    read_link_structure,
    sanity_main,
    verify_integrity,
)
from tests import _get_test_root


def test_read_folder_structure(tmpdir):
    with tmpdir.as_cwd():
        os.mkdir("2012.01.rc1")
        os.mkdir("2012.01.rc2")
        os.mkdir("bleeding")
        os.mkdir("2012.01.12")
        os.mkdir("nowhere")

        os.symlink("2012.01.12", "2012.01")
        os.symlink("2012.01", "stable")
        os.symlink("2012.01.rc2", "testing")
        os.symlink("nowhere", "bleeding-20242012-2313-py311")
        os.symlink("nowhere", "bleeding-something.deleteme")

        expected_result = {
            "root_folder": tmpdir,
            "root_links": ["stable", "testing"],
            "links": {
                "2012.01": "2012.01.12",
                "stable": "2012.01",
                "testing": "2012.01.rc2",
            },
        }

        output_dict = read_link_structure(os.getcwd())

        assert isinstance(output_dict, dict)
        assert equal_links(output_dict, expected_result)


def test_create_symlinks(tmpdir):
    links_dict = {
        "root_folder": tmpdir,
        "links": {
            "2012.01": "2012.01.12",
            "stable": "2012.01",
            "testing": "2012.01.rc2",
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
        assert os.path.realpath("testing") == os.path.realpath("2012.01.rc2")


def test_create_symlink_stdout(tmpdir, capsys):
    links_dict = {
        "root_folder": tmpdir,
        "links": {
            "2023": "2023.07",
        },
    }
    with tmpdir.as_cwd():
        os.mkdir("2023.07")
        create_symlinks(links_dict)
        captured = capsys.readouterr()
        assert captured.out == "Created new symlink 2023 pointing to 2023.07\n"


def test_overwrite_symlink_stdout(tmpdir, capsys):
    links_dict = {
        "root_folder": tmpdir,
        "links": {
            "2023": "2023.07",
        },
    }
    with tmpdir.as_cwd():
        os.mkdir("2023.06")
        os.mkdir("2023.07")
        os.symlink("2023.06", "2023")
        create_symlinks(links_dict)
        captured = capsys.readouterr()
        print(captured.out)
        assert captured.out == "Existing symlink 2023 moved from 2023.06 to 2023.07.\n"


def test_overwrite_symlink_implicit_multiple_stdout(tmpdir, capsys):
    links_dict = {
        "root_folder": tmpdir,
        "links": {
            "stable": "stable-py38",
            "stable-py38": "2023.09.03",
            "azure-stable": "azure-stable-py38",
            "azure-stable-py38": "stable-py38",
            "2023.09.03": "2023.09.03-rc4",
        },
    }
    with tmpdir.as_cwd():
        os.mkdir("2023.09.03-rc4")
        os.mkdir("2023.09.03-rc3")
        os.symlink("stable-py38", "stable")
        os.symlink("azure-stable-py38", "azure-stable")
        os.symlink("stable-py38", "azure-stable-py38")
        os.symlink("2023.09.03", "stable-py38")
        os.symlink("2023.09.03-rc3", "2023.09.03")
        create_symlinks(links_dict)
        captured = capsys.readouterr()
        print(captured.out)
        assert (
            captured.out
            == "Existing symlink 2023.09.03 moved from 2023.09.03-rc3 to 2023.09.03-rc4. Some symlinks were implicitly moved due to this: stable, azure-stable.\n"
        )


def test_integration(tmpdir):
    test_folder = _get_test_root()
    shutil.copy(os.path.join(test_folder, "data/links.json"), tmpdir)
    with tmpdir.as_cwd():
        with open("links.json", encoding="utf-8") as link_file:
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
        with open("links.json", encoding="utf-8") as link_file:
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
            "root_links": ["stable", "testing"],
            "links": {
                "2012.01": "2012.01.12",
                "stable": "2012.01",
                "testing": "2012.01.rc2",
            },
        }

        errors = verify_integrity(test_dict)
        assert errors == []

        test_dict["links"]["bleeding"] = "bleeding_py3"
        errors = verify_integrity(test_dict)
        assert errors == ["bleeding_py3 does not exist"]

        test_dict["links"]["2012.01.rc2"] = "testing"
        errors = verify_integrity(test_dict)
        assert "2012.01.rc2 is part of a cyclic symlink" in errors
        assert "testing is part of a cyclic symlink" in errors


def test_root_folder_error(tmpdir):
    with tmpdir.as_cwd():
        os.mkdir("2012.01.12")

        test_dict = {
            "root_folder": os.path.join(str(tmpdir), "non_existing"),
            "root_links": ["stable", "testing"],
            "links": {
                "2012.01": "2012.01.12",
                "stable": "2012.01",
                "testing": "2012.01.rc2",
            },
        }

        with pytest.raises(ValueError) as value_error:
            create_symlinks(test_dict)
        assert "does not exist" in str(value_error.value)

        test_dict["root_folder"] = os.path.relpath(str(tmpdir))
        with pytest.raises(ValueError) as value_error:
            create_symlinks(test_dict)
        assert "is not absolute" in str(value_error.value)


def test_link_error(tmpdir):
    with tmpdir.as_cwd():
        os.mkdir("2012.01.12")

        test_dict = {
            "root_folder": tmpdir,
            "root_links": ["stable", "testing"],
            "links": {
                "2012.01": "2012.01.12",
                "stable": "2012.01",
                "testing": "2012.01.rc2",
            },
        }
        with pytest.raises(ValueError) as value_error:
            create_symlinks(test_dict)
        assert str(value_error.value) == "2012.01.rc2 does not exist"


def test_root_link_error(tmpdir):
    with tmpdir.as_cwd():
        os.mkdir("2012.01.12")

        test_dict = {
            "root_folder": tmpdir,
            "root_links": ["stable", "testing"],
            "links": {
                "2012.01": "2012.01.12",
                "stable": "2012.01",
                "testing": "2012.01.rc2",
            },
        }
        with pytest.raises(ValueError) as value_error:
            create_symlinks(test_dict)
        assert str(value_error.value) == "2012.01.rc2 does not exist"


def test_executables(tmpdir):
    old_argv = sys.argv.copy()
    sys.argv = ["run", "links_test.json"]
    try:
        test_folder = _get_test_root()
        with open(
            os.path.join(test_folder, "data/links_full.json"), encoding="utf-8"
        ) as input_file:
            input_data = json.load(input_file)

        with tmpdir.as_cwd():
            input_data["root_folder"] = str(tmpdir)
            with open("links_test.json", "w", encoding="utf-8") as test_file:
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


def test_sort_lists_in_dicts():
    assert _sort_lists_in_dicts({1: [2, 1]}) == {1: [1, 2]}


def test_compare_dicts_handles_non_sorted_lists():
    assert _compare_dicts({1: [2, 1]}, {1: [1, 2]}).strip() == "{1: [1, 2]}"
