from argparse import Namespace
from base64 import b64encode
from unittest.mock import ANY, MagicMock

import pytest

from komodo.symlink.suggester.cli import suggest_symlink_configuration
from komodo.symlink.suggester.configuration import Configuration, update
from komodo.symlink.suggester.release import Release


@pytest.mark.parametrize(
    ("test_input", "expected"),
    [
        ("releases/2019.12.00-py27.yml", "2019.12.00-py27"),
        ("releases/2019.12.rc0.yml", "2019.12.rc0"),
    ],
)
def test_release_from_file_name(test_input, expected):
    assert Release.id_from_file_name(test_input) == expected


@pytest.mark.parametrize(
    ("release_a", "release_b", "expected"),
    [
        ("2019.12.00-py27", "2019.12.rc0", 0),
        ("2019.12.00-py27", "2019.07.02", 5),
        ("2019.12.rc0-py27", "2020.02.a0-py37", -2),
    ],
)
def test_monthly_diff_releases(release_a, release_b, expected):
    r_a = Release(release_a)
    r_b = Release(release_b)
    assert r_a.monthly_diff(r_b) == expected


@pytest.mark.parametrize(
    ("test_input", "expected"),
    [("foo/bar.yml", False), ("releases/foo.yml", True), ("foo.yml", False)],
)
def test_path_is_release(test_input, expected):
    assert Release.path_is_release(test_input) == expected


@pytest.mark.parametrize(
    ("release_id", "expected"),
    [
        ("2019.12.00-py3", "py3"),
        ("2019.12.00-py27", "py27"),
        ("2019.12.00-py38", "py38"),
        ("2019.12.00-py311", "py311"),
        ("2019.12.00-py312", "py312"),
    ],
)
def test_py_ver(release_id, expected):
    release = Release(release_id)
    assert release.py_ver() == expected


@pytest.mark.parametrize(
    ("conf", "link", "concrete"),
    [
        # testing happy path
        (
            {
                "links": {
                    "testing-py27": "1349.01-py27",
                    "1349.01-py27": "1349.02-py27",
                    "1349.02-py27": "1349.01.a0-py27",
                },
            },
            "testing-py27",
            "1349.01.a0-py27",
        ),
    ],
)
def test_get_concrete_release(conf, link, concrete):
    conf = Configuration(conf)
    assert repr(conf._get_concrete_release(link)) == concrete


@pytest.mark.parametrize(
    ("json_in", "release_id", "mode", "changed", "json_out"),
    [
        # testing happy path
        (
            """{"links": {
"testing-py27": "1994.12.00.rc0-py27",
"1994.12-py27" : "1994.12.00.rc0-py27"}}""",
            "1994.12.00.rc1-py27",
            "testing",
            "changed",
            """{
    "links": {
        "1994.12-py27": "1994.12.00.rc0-py27",
        "testing-py27": "1994.12.00.rc1-py27"
    }
}
""",
        ),
        # testing promotion from previous release
        (
            """{"links": {
"2001.11-py27": "2001.11.00-py27",
"stable-py27" : "2001.11-py27",
"testing-py27": "2001.11.00.rc0-py27"}}""",
            "2001.12.rc0-py27",
            "testing",
            "changed",
            """{
    "links": {
        "2001.11-py27": "2001.11.00-py27",
        "stable-py27": "2001.11-py27",
        "testing-py27": "2001.12.rc0-py27"
    }
}
""",
        ),
        # do not overwrite month aliases in links if e.g. testing links to
        # a month alias
        (
            """{"links": {
"2010.12-py27": "2010.12.rc0-py27",
"stable-py27" : "2010.11.00-py27",
"testing-py27": "2010.12-py27"
}}""",
            "2010.12.rc1-py27",
            "testing",
            "changed",
            """{
    "links": {
        "2010.12-py27": "2010.12.rc1-py27",
        "stable-py27": "2010.11.00-py27",
        "testing-py27": "2010.12-py27"
    }
}
""",
        ),
        # stable, new month alias
        (
            """{"links": {
"2015.12-py27": "2015.12.03-py27",
"stable-py27" : "2015.12-py27"}}""",
            "2016.01.00-py27",
            "stable",
            "changed",
            """{
    "links": {
        "2015.12-py27": "2015.12.03-py27",
        "2016.01-py27": "2016.01.00-py27",
        "stable-py27": "2016.01-py27"
    }
}
""",
        ),
        # stable, existing month alias
        (
            """{"links": {
"2024.12-py27": "2024.12.03-py27",
"2025.01-py27": "2025.01.rc3-py27",
"stable-py27" : "2024.12-py27"}}""",
            "2025.01.00-py27",
            "stable",
            "changed",
            """{
    "links": {
        "2024.12-py27": "2024.12.03-py27",
        "2025.01-py27": "2025.01.00-py27",
        "stable-py27": "2025.01-py27"
    }
}
""",
        ),
        # non-existent stable and testing
        (
            """{"links": {}}""",
            "2035.01.rc0-py27",
            "testing",
            "changed",
            """{
    "links": {
        "testing-py27": "2035.01.rc0-py27"
    }
}
""",
        ),
        # mix between postfixed and non-postfixed aliases
        (
            """{"links": {
        "2019.12": "2019.12.02-py27",
        "2020.02-py27": "2020.02.rc2-py27",
        "stable-py2": "stable-py27",
        "stable-py27": "2019.12",
        "testing-py2": "testing-py27",
        "testing-py27": "2020.02-py27"
    }}""",
            "2020.02.rc3-py27",
            "testing",
            "changed",
            """{
    "links": {
        "2019.12": "2019.12.02-py27",
        "2020.02-py27": "2020.02.rc3-py27",
        "stable-py2": "stable-py27",
        "stable-py27": "2019.12",
        "testing-py2": "testing-py27",
        "testing-py27": "2020.02-py27"
    }
}
""",
        ),
        # suggest testing update after skipped month
        (
            """{"links": {
        "2020.11-py37": "2020.11.04-py37",
        "2020.12-py37": "2020.12.rc2-py37",
        "stable-py3": "stable-py37",
        "stable-py37": "2020.11-py37",
        "testing-py3": "testing-py37",
        "testing-py37": "2020.12-py37"
    }}""",
            "2021.01.rc3-py37",
            "testing",
            "changed",
            """{
    "links": {
        "2020.11-py37": "2020.11.04-py37",
        "2020.12-py37": "2020.12.rc2-py37",
        "2021.01-py37": "2021.01.rc3-py37",
        "stable-py3": "stable-py37",
        "stable-py37": "2020.11-py37",
        "testing-py3": "testing-py37",
        "testing-py37": "2021.01-py37"
    }
}
""",
        ),
    ],
)
def test_update(json_in, release_id, mode, changed, json_out):
    assert update(json_in, release_id, mode) == (json_out, changed == "changed")


def _mock_repo(sym_config):
    repo = MagicMock()
    repo.get_contents.return_value = Namespace(
        content=b64encode(sym_config.encode()),
        sha="123",
    )
    return repo


@pytest.mark.parametrize(
    ("symlink_file", "mode"),
    [
        ("foo.json", "stable"),
        ("foo_azure.json", "stable"),
    ],
)
def test_suggest_symlink_configuration(symlink_file, mode):
    """Testing whether when updating symlink file the branch gets a corresponding name."""
    config = """{"links": {
"2050.02-py58": "2050.02.00-py58",
"stable-py58": "2050.02-py58"
}}"""
    repo = _mock_repo(config)

    args = Namespace(
        git_ref="master",
        release="2050.02.01-py58",
        mode=mode,
        joburl="http://job",
        jobname="job",
        config_files=symlink_file,
        python_versions="py58",
    )
    suggest_symlink_configuration(args, repo)

    repo.get_contents.assert_called_once_with(symlink_file, ref="master")
    repo.get_branch.assert_called_once_with("master")
    repo.create_git_ref.assert_called_once_with(
        ref=f"refs/heads/2050.02.01-py58/{mode}",
        sha=ANY,
    )
    repo.update_file.assert_called_once_with(
        symlink_file,
        f"Update {mode} symlinks for 2050.02.01-py58",
        """{
    "links": {
        "2050.02-py58": "2050.02.01-py58",
        "stable-py58": "2050.02-py58"
    }
}
""",
        ANY,
        branch=f"2050.02.01-py58/{mode}",
    )
    repo.create_pull.assert_called_once_with(
        title=ANY,
        body=ANY,
        head=f"2050.02.01-py58/{mode}",
        base="master",
    )


def test_noop_suggestion():
    config = """{"links": {
"2050.02-py58": "2050.02.00-py58",
"stable-py58": "2050.02-py58"
}}"""
    repo = _mock_repo(config)

    args = Namespace(
        git_ref="master",
        release="2050.02.00-py58",
        mode="stable",
        joburl="http://job",
        jobname="job",
        config_files="foo.json",
        python_versions="py58",
    )

    repo.create_pull.assert_not_called()

    assert suggest_symlink_configuration(args, repo) is None


def test_suggest_symlink_multi_configuration():
    config = """{"links": {
"2050.02-py58": "2050.02.00-py58",
"stable-py58": "2050.02-py58"
}}"""
    repo = _mock_repo(config)
    mode = "stable"
    args = Namespace(
        git_ref="master",
        release="2050.02.01-py58",
        mode=mode,
        joburl="http://job",
        jobname="job",
        config_files="foo.json, foo_azure.json",
        python_versions="py38, py311",
    )
    suggest_symlink_configuration(args, repo)


@pytest.mark.parametrize(
    ("json_in", "release_id", "mode", "changed", "json_out"),
    [  # testing happy path
        (
            """{"links": {
            "testing-py38": "1994.12.00.rc0-py38",
            "1994.12-py38": "1994.12.00.rc0-py38",
            "testing-py311": "1994.12.00.rc0-py311",
            "1994.12-py311": "1994.12.00.rc0-py311"}}""",
            "1994.12.00.rc1-py38",
            "testing",
            "changed",
            """{
    "links": {
        "1994.12-py311": "1994.12.00.rc0-py311",
        "1994.12-py38": "1994.12.00.rc0-py38",
        "testing-py311": "1994.12.00.rc1-py311",
        "testing-py38": "1994.12.00.rc1-py38"
    }
}
""",
        ),
        # testing promotion from previous release
        (
            """{"links": {
        "2001.11-py38": "2001.11.00-py38",
        "2001.11-py311": "2001.11.00-py311",
        "stable-py38" : "2001.11-py38",
        "testing-py38": "2001.11.rc0-py38",
        "stable-py311" : "2001.11-py311",
        "testing-py311": "2001.11.rc0-py311"}}""",
            "2001.12.rc0-py38",
            "testing",
            "changed",
            """{
    "links": {
        "2001.11-py311": "2001.11.00-py311",
        "2001.11-py38": "2001.11.00-py38",
        "stable-py311": "2001.11-py311",
        "stable-py38": "2001.11-py38",
        "testing-py311": "2001.12.rc0-py311",
        "testing-py38": "2001.12.rc0-py38"
    }
}
""",
        ),
    ],
)
def test_multi_update(json_in, release_id, mode, changed, json_out):
    assert update(json_in, release_id, mode, ["py38", "py311"]) == (
        json_out,
        changed == "changed",
    )
