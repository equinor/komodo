import os
import re
import sys
import warnings
from contextlib import contextmanager
from unittest import mock

import pytest
import yaml

from komodo import lint_maturity
from komodo.lint_maturity import get_release_version
from komodo.lint_maturity import main as lint_maturity_main
from komodo.yaml_file_types import ReleaseFile


def _create_tmp_test_files(release_sample, file_names_sample):
    folder_name = os.path.join(os.getcwd(), "test_lint_maturity/")
    dummy_folder_name = os.path.join(os.getcwd(), "test_lint_maturity/dummy_folder")
    os.mkdir(folder_name)
    os.mkdir(dummy_folder_name)
    list_files = []

    for file_name in file_names_sample:
        list_files.append(folder_name + file_name)

        with open(folder_name + file_name, "w", encoding="utf-8") as file_sample:
            file_sample.write(release_sample)

    return list_files


@pytest.mark.parametrize(
    ("release_basename", "release_version", "count_tag_invalid"),
    [
        ("2020.02.01-py38-rhel7.yml", "stable", 4),
        ("2020.02.a1-py38-rhel7.yml", "a", 1),
        ("2020.02.b1-py38-rhel7.yml", "b", 2),
        ("2020.02.rc1-py38-rhel7.yml", "rc", 3),
    ],
)
def test_msg_packages_invalid(release_basename, release_version, count_tag_invalid):
    exit_msg = lint_maturity.msg_packages_invalid(
        release_basename,
        release_version,
        count_tag_invalid,
        dict_tag_maturity={
            "a": [("package_a1", "v3.1.a1")],
            "b": [("package_b1", "v3.1.b1")],
            "rc": [("package_rc1", "v3.1.rc1")],
            "stable": [("package_st1", "v0.10.4")],
            "invalid": [("package_iv1", "5.13.1-src")],
            "exception": [("package_ex2", "testing/2020.3/rc1")],
        },
    )

    expected_system_exit = """2020.02.01-py38-rhel7.yml has 4 packages with invalid maturity tag.
\tTag a packages: [('package_a1', 'v3.1.a1')]
\tTag b packages: [('package_b1', 'v3.1.b1')]
\tTag rc packages: [('package_rc1', 'v3.1.rc1')]
\tTag invalid packages: [('package_iv1', '5.13.1-src')]

2020.02.a1-py38-rhel7.yml has 1 packages with invalid maturity tag.
\tTag invalid packages: [('package_iv1', '5.13.1-src')]

2020.02.b1-py38-rhel7.yml has 2 packages with invalid maturity tag.
\tTag a packages: [('package_a1', 'v3.1.a1')]
\tTag invalid packages: [('package_iv1', '5.13.1-src')]

2020.02.rc1-py38-rhel7.yml has 3 packages with invalid maturity tag.
\tTag a packages: [('package_a1', 'v3.1.a1')]
\tTag b packages: [('package_b1', 'v3.1.b1')]
\tTag invalid packages: [('package_iv1', '5.13.1-src')]

"""  # noqa

    assert exit_msg in expected_system_exit


def test_msg_packages_exception():
    release_file_names = [
        "2020.02.01-py38-rhel7.yml",
        "2020.02.a1-py38-rhel7.yml",
        "2020.02.b1-py38-rhel7.yml",
        "2020.02.rc1-py38-rhel7.yml",
        "bleeding.yml",
    ]

    for file_basename in release_file_names:
        expected_warning_msg = file_basename + ", exception list of packages:\n"
        expected_warning_msg += (
            "\t" + str([("package_ex2", "testing/2020.3/rc1")]) + "\n"
        )
        warning_msg = lint_maturity.msg_packages_exception(
            file_basename,
            dict_tag_maturity={
                "a": [("package_a1", "v3.1.a1")],
                "b": [("package_b1", "v3.1.b1")],
                "rc": [("package_rc1", "v3.1.rc1")],
                "stable": [("package_st1", "v0.10.4")],
                "invalid": [("package_iv1", "5.13.1-src")],
                "exception": [("package_ex2", "testing/2020.3/rc1")],
            },
        )

        assert warning_msg == expected_warning_msg


@pytest.mark.parametrize(
    ("invalid_tags", "expected_n_invalid_tags_release"),
    [
        (["invalid"], 1),
        (["a", "invalid"], 2),
        (["a", "b", "invalid"], 3),
        (["a", "b", "rc", "invalid"], 4),
    ],
)
def test_count_invalid_tags(invalid_tags, expected_n_invalid_tags_release):
    n_invalid_tags = lint_maturity.count_invalid_tags(
        dict_tag_maturity={
            "a": [("package_a1", "v3.1.a1")],
            "b": [("package_b1", "v3.1.b1")],
            "rc": [("package_rc1", "v3.1.rc1")],
            "stable": [("package_st1", "v0.10.4")],
            "invalid": [("package_iv1", "5.13.1-src")],
            "exception": [("package_ex2", "testing/2020.3/rc1")],
        },
        invalid_tags=invalid_tags,
    )

    assert expected_n_invalid_tags_release == n_invalid_tags


@pytest.mark.parametrize(
    ("version_string", "expected_release_type"),
    [
        ("2020.02.01", "stable"),
        ("2020.02.a1", "a"),
        ("2020.02.b1", "b"),
        ("2020.02.rc1", "rc"),
        ("bleeding", "invalid"),
    ],
)
def test_get_release_type(version_string, expected_release_type):
    release_type = lint_maturity.get_release_type(version_string)

    assert release_type == expected_release_type


def test_get_packages_info():
    dict_tag_maturity = lint_maturity.get_packages_info(
        release_file=ReleaseFile.from_yaml_string(
            value=yaml.dump(
                {
                    "package_a1": "v3.1.a1",
                    "package_b1": "v3.1.b1",
                    "package_rc1": "v3.1.rc1",
                    "package_st1": "v0.10.4",
                    "package_iv1": "5.13.1-src",
                    "package_ex2": "testing/2020.3/rc1",
                },
            ),
        ),
        tag_exceptions_package=["package_ex2"],
    )

    expected_dict_tag_maturity = {
        "a": [("package_a1", "v3.1.a1")],
        "b": [("package_b1", "v3.1.b1")],
        "rc": [("package_rc1", "v3.1.rc1")],
        "stable": [("package_st1", "v0.10.4")],
        "invalid": [("package_iv1", "5.13.1-src")],
        "exception": [("package_ex2", "testing/2020.3/rc1")],
    }

    for tag, packages in expected_dict_tag_maturity.items():
        assert dict_tag_maturity[tag] == packages


def test_read_yaml_file(tmpdir):
    with tmpdir.as_cwd():
        list_files = _create_tmp_test_files(
            release_sample="""release: ['bleeding', 'rpath']
package: ['package_ex2']""",
            file_names_sample=["2020.02.01.yml"],
        )

    loaded_yaml_file = lint_maturity.read_yaml_file(list_files[0])

    assert loaded_yaml_file["release"] == ["bleeding", "rpath"]
    assert loaded_yaml_file["package"] == ["package_ex2"]


def test_msg_release_exception():
    expected_release_version = ["stable", "a", "b", "rc", "exception"]
    release_file_names = [
        "2020.02.01-py38-rhel7.yml",
        "2020.02.a1-py38-rhel7.yml",
        "2020.02.b1-py38-rhel7.yml",
        "2020.02.rc1-py38-rhel7.yml",
        "bleeding-py38-rhel7.yml",
    ]

    for count, release_basename in enumerate(release_file_names):
        release_version = expected_release_version[count]
        expected_warning_msg = ""

        if release_basename == "bleeding-py38-rhel7.yml":
            expected_warning_msg += (
                release_basename + " not lint because it is in the exception list.\n"
            )

        warning_msg = lint_maturity.msg_release_exception(
            release_basename,
            release_version,
        )

        assert warning_msg == expected_warning_msg


@pytest.mark.parametrize(
    ("release_basename", "expected_release_version"),
    [
        ("2020.02.01-py38-rhel7.yml", "stable"),
        ("2020.02.a1-py38-rhel7.yml", "a"),
        ("2020.02.b1-py38-rhel7.yml", "b"),
        ("2020.02.rc1-py38-rhel7.yml", "rc"),
        ("bleeding", "exception"),
        ("invalid_tag", "invalid"),
    ],
)
def test_get_release_version(release_basename, expected_release_version):
    release_version = get_release_version(
        release_basename=release_basename,
        tag_exceptions_release=["bleeding", "rpath"],
    )

    assert release_version == expected_release_version


def test_lint_maturity_run(tmpdir):
    with tmpdir.as_cwd():
        list_files = _create_tmp_test_files(
            release_sample="""package_a1: v3.1.a1
package_b1: v3.1.b1
package_rc1: v3.1.rc1
package_st1: v0.10.4
package_iv1: 5.13.1-src
package_ex2: testing/2020.3/rc1""",
            file_names_sample=[
                "2020.02.01-py38-rhel7.yml",
                "2020.02.a1-py38-rhel7.yml",
                "2020.02.b1-py38-rhel7.yml",
                "2020.02.rc1-py38-rhel7.yml",
            ],
        )

        expected_warning = """2020.02.01-py38-rhel7.yml, exception list of packages:
\t[('package_ex2', 'testing/2020.3/rc1')]
2020.02.a1-py38-rhel7.yml, exception list of packages:
\t[('package_ex2', 'testing/2020.3/rc1')]
2020.02.b1-py38-rhel7.yml, exception list of packages:
\t[('package_ex2', 'testing/2020.3/rc1')]
2020.02.rc1-py38-rhel7.yml, exception list of packages:
\t[('package_ex2', 'testing/2020.3/rc1')]
bleeding-py38-rhel7.yml not lint because it is in the exception list.
bleeding, exception list of packages:
\t[('package_ex2', 'testing/2020.3/rc1')]
bleeding has 4 packages with invalid maturity tag.
\tTag a packages: [('package_a1', 'v3.1.a1')]
\tTag b packages: [('package_b1', 'v3.1.b1')]
\tTag rc packages: [('package_rc1', 'v3.1.rc1')]
\tTag invalid packages: [('package_iv1', '5.13.1-src')]
"""

        expected_system_exit = """2020.02.01-py38-rhel7.yml has 4 packages with invalid maturity tag.
\tTag a packages: [('package_a1', 'v3.1.a1')]
\tTag b packages: [('package_b1', 'v3.1.b1')]
\tTag rc packages: [('package_rc1', 'v3.1.rc1')]
\tTag invalid packages: [('package_iv1', '5.13.1-src')]

2020.02.a1-py38-rhel7.yml has 1 packages with invalid maturity tag.
\tTag invalid packages: [('package_iv1', '5.13.1-src')]

2020.02.b1-py38-rhel7.yml has 2 packages with invalid maturity tag.
\tTag a packages: [('package_a1', 'v3.1.a1')]
\tTag invalid packages: [('package_iv1', '5.13.1-src')]

2020.02.rc1-py38-rhel7.yml has 3 packages with invalid maturity tag.
\tTag a packages: [('package_a1', 'v3.1.a1')]
\tTag b packages: [('package_b1', 'v3.1.b1')]
\tTag invalid packages: [('package_iv1', '5.13.1-src')]

"""  # noqa

    for list_file in list_files:
        with pytest.raises(SystemExit) as exit_info, warnings.catch_warnings(
            record=True,
        ) as warning_info:
            lint_maturity.run(
                files_to_lint=[list_file],
                tag_exceptions={
                    "release": ["bleeding", "rpath"],
                    "package": ["package_ex2"],
                },
            )
        print(warning_info[0].message)
        assert str(warning_info[0].message) in expected_warning
        assert str(exit_info.value) in expected_system_exit


def test_get_files_to_lint(tmpdir):
    with tmpdir.as_cwd():
        list_files_expected = _create_tmp_test_files(
            release_sample="pytest: 3.1.2",
            file_names_sample=[
                "2020.02.01-py38-rhel7.yml",
                "2020.02.a1-py38-rhel7.yml",
                "2020.02.b1-py38-rhel7.yml",
                "2020.02.rc1-py38-rhel7.yml",
                "bleeding-py38-rhel7.yml",
            ],
        )

    list_file = lint_maturity.get_files_to_lint(
        release_file=list_files_expected[0],
        release_folder=None,
    )
    assert list_files_expected[0] == list_file[0]

    list_files = lint_maturity.get_files_to_lint(
        release_file=None,
        release_folder=str(os.path.dirname(list_files_expected[0])),
    )

    assert set(list_files_expected) == set(
        list_files,
    )  # python3 was running without set(), but travis did not


def test_define_tag_exceptions(tmpdir):
    with tmpdir.as_cwd():
        tag_exception_file_name = _create_tmp_test_files(
            release_sample="""release: ['bleeding', 'rpath']
package: ['package_ex2']""",
            file_names_sample=["tag_exceptions.yml"],
        )

    assert lint_maturity.define_tag_exceptions(tag_exception_file_name) == {
        "release": ["bleeding", "rpath"],
        "package": ["package_ex2"],
    }

    tag_exception_file_name = [""]

    assert lint_maturity.define_tag_exceptions(tag_exception_file_name) == {
        "release": [],
        "package": [],
    }

    tag_exception_file_name = ["invalid_path"]

    with pytest.raises(
        SystemExit,
        match=re.escape("['invalid_path'] is not a valid file."),
    ):
        lint_maturity.define_tag_exceptions(tag_exception_file_name)


def test_main(monkeypatch, tmpdir):
    with tmpdir.as_cwd():
        list_files_expected = _create_tmp_test_files(
            release_sample="",
            file_names_sample=[
                "2020.02.01.yml",
                "2020.02.a1.yml",
                "2020.02.b1.yml",
                "2020.02.rc1.yml",
                "bleeding.yml",
            ],
        )

    args = mock.Mock()
    args.tag_exceptions = [""]
    args.release_folder = [os.path.dirname(list_files_expected[0])]
    args.release_file = None

    parser_mock = mock.Mock()
    parser_mock.parse_args.return_value = args

    get_parser_mock = mock.Mock(return_value=parser_mock)
    tag_exceptions_mock = mock.Mock(return_value={"release": [], "package": []})
    files_to_lint_mock = mock.Mock(return_value=list_files_expected)
    run_mock = mock.Mock()

    monkeypatch.setattr(lint_maturity, "get_parser", get_parser_mock)
    monkeypatch.setattr(lint_maturity, "define_tag_exceptions", tag_exceptions_mock)
    monkeypatch.setattr(lint_maturity, "get_files_to_lint", files_to_lint_mock)
    monkeypatch.setattr(lint_maturity, "run", run_mock)

    lint_maturity.main()

    tag_exceptions_mock.assert_called_once_with(tag_exception_arg=[""])
    files_to_lint_mock.assert_called_once_with(
        release_folder=args.release_folder,
        release_file=args.release_file,
    )
    run_mock.assert_called_once_with(
        list_files_expected,
        {"release": [], "package": []},
    )


def test_integration_main(monkeypatch, tmpdir):
    with tmpdir.as_cwd():
        list_files_expected = _create_tmp_test_files(
            release_sample="""package_a1: v3.1.a1
package_b1: v3.1.b1
package_rc1: v3.1.rc1
package_st1: v0.10.4
package_iv1: 5.13.1-src
package_ex2: testing/2020.3/rc1""",
            file_names_sample=["2020.02.01-py38-rhel7.yml"],
        )
    monkeypatch.setattr(
        sys,
        "argv",
        ["", "--release_folder", os.path.dirname(list_files_expected[0])],
    )

    with pytest.raises(
        SystemExit,
        match=r"(.*\n.*){5}",  # five errors + one formatting message
    ):
        lint_maturity_main()


@contextmanager
def does_not_raise():
    yield


@pytest.mark.parametrize(
    ("yaml_string", "expectation"),
    [
        pytest.param(
            """pytest: "3.2"\ntestlib: 2.3.3""",
            does_not_raise(),
            id="valid_yaml_input",
        ),
        pytest.param(
            """pytest: 3.2\ntestlib: 2.3.3""",
            pytest.raises(
                SystemExit,
                match=r"Package 'pytest' has invalid version type \(3.2\)",
            ),
            id="invalid_yaml__float_package_version",
        ),
        pytest.param(
            """pytest: "3.2"\npytest: 3.2.1\nttestlib: 2.3.3""",
            pytest.raises(
                SystemExit,
                match='found duplicate key "pytest"',
            ),
            id="invalid_release_file__duplicate_packages",
        ),
    ],
)
def test_argument_types(yaml_string: str, expectation, monkeypatch, tmpdir):
    with tmpdir.as_cwd():
        list_files_expected = _create_tmp_test_files(
            release_sample=yaml_string,
            file_names_sample=["2020.02.01-py38-rhel7.yml"],
        )
    monkeypatch.setattr(sys, "argv", ["", "--release_file", list_files_expected[0]])
    with expectation:
        lint_maturity.main()
