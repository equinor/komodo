import pytest

from komodo.lint_symlink_config import lint_symlink_config
from komodo.symlink.sanity_check import assert_root_nodes, suggest_missing_roots


def test_suggest_missing_root_links():
    link_dict = {
        "links": {
            "stable": "2012.01",
            "testing": "2012.03",
            "deprecated-py38": "2011.11",
            "deprecated-py311": "2011.12",
        },
        "root_links": ["stable", "testing"],
    }

    assert suggest_missing_roots(link_dict) == sorted(
        ["deprecated-py311", "deprecated-py38"]
    )


def test_assert_root_nodes_error_message_missing_roots():
    link_dict = {
        "links": {
            "stable": "2012.01",
            "testing": "2012.03",
            "missing_root_1": "2011.12",
            "missing_root_2": "2011.11",
            "missing_root_3": "2011.10",
        },
        "root_links": ["stable", "testing"],
    }

    with pytest.raises(
        AssertionError,
        match=r"Missing root\(s\): \[(?=.*missing_root_1)(?=.*missing_root_2)(?=.*missing_root_3)",
    ):
        assert_root_nodes(link_dict)


def test_assert_root_nodes_error_message_incorrectly_added_roots():
    link_dict = {
        "links": {
            "stable": "2012.01",
            "testing": "2012.03",
            "deprecated": "testing",
        },
        "root_links": ["deprecated", "stable", "testing"],
    }

    with pytest.raises(
        AssertionError,
        match=r"Incorrectly added root\(s\): \['testing'\]",
    ):
        assert_root_nodes(link_dict)


def test_symlink_config_detect_missing_intermediate_link():
    link_dict = {
        "links": {
            "stable": "2012.01",
            "2012.01": "2012.01.04-py38",
            "testing": "2012.03",
            "2012.03": "2012.03.rc4-py38",
            "deprecated": "testing",
            "testing-py311": "2024.05-py311",
        },
        "root_links": ["deprecated", "stable", "testing-py311"],
    }
    with pytest.raises(
        SystemExit,
        match=r"Missing symlink 2024.05-py311",
    ):
        lint_symlink_config(link_dict)
