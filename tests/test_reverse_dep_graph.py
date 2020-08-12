import pytest

from komodo import reverse_dep_graph
import json

REPO = {
    "package_a": {
        "1.2.3": {
            "depends": ["package_b", "package_c", "package_e", "package_f"],
            "maintainer": "a@b.c",
            "make": "pip",
            "source": "pypi",
        }
    },
    "package_b": {
        "2.3.4": {"maintainer": "a@b.c", "make": "pip", "source": "pypi"},
        "1.0.0": {"maintainer": "a@b.c", "make": "pip", "source": "pypi"},
    },
    "package_c": {
        "0.0.1": {
            "depends": ["package_d", "package_e"],
            "maintainer": "a@b.c",
            "make": "pip",
            "source": "pypi",
        }
    },
    "package_d": {
        "10.2.1": {
            "depends": ["package_e"],
            "maintainer": "a@b.c",
            "make": "pip",
            "source": "pypi",
        }
    },
    "package_e": {"4.1.2": {"maintainer": "a@b.c", "make": "pip", "source": "pypi"}},
    "package_f": {
        "0.1.2": {"maintainer": "a@b.c", "make": "pip", "source": "pypi"},
        "1.0.2": {"maintainer": "a@b.c", "make": "pip", "source": "pypi"},
    },
}

BASE_RELEASE = {
    "package_a": "1.2.3",
    "package_b": "2.3.4",
    "package_c": "0.0.1",
    "package_d": "10.2.1",
    "package_e": "4.1.2",
    "package_f": "1.0.2",
}

REPO_MISSING_PKG = {
    "package_a": {
        "1.2.3": {
            "depends": ["package_b"],
            "maintainer": "a@b.c",
            "make": "pip",
            "source": "pypi",
        }
    }
}


def test_extract_reverse_list():
    rev_deps = reverse_dep_graph.build_reverse(BASE_RELEASE, REPO)
    print(rev_deps)
    assert len(rev_deps) == 5  # a does not have dependants
    assert rev_deps["package_b"].difference({("package_a", "1.2.3")}) == set()
    assert rev_deps["package_c"].difference({("package_a", "1.2.3")}) == set()
    assert (
        rev_deps["package_e"].difference(
            {("package_c", "0.0.1"), ("package_d", "10.2.1"), ("package_a", "1.2.3")}
        )
        == set()
    )
    assert rev_deps["package_f"].difference({("package_a", "1.2.3")}) == set()
    assert rev_deps["package_d"].difference({("package_c", "0.0.1")}) == set()


def test_extract_missing_pkg_in_repo():
    with pytest.raises(SystemExit) as exit_info:
        reverse_dep_graph.build_reverse(BASE_RELEASE, REPO_MISSING_PKG)
    assert "No package package_b in repo" in str(exit_info.value)


def test_extract_reverse_graph():
    rev_deps = reverse_dep_graph.build_reverse(BASE_RELEASE, REPO)
    rev_dep_graph = reverse_dep_graph.reverse_deps("package_e", "4.1.2", rev_deps)
    expected = {
        "package_e-4.1.2": [
            {"package_d-10.2.1": [{"package_c-0.0.1": [{"package_a-1.2.3": []}]}]},
            {"package_c-0.0.1": [{"package_a-1.2.3": []}]},
            {"package_a-1.2.3": []},
        ]
    }

    assert _sort_graph(rev_dep_graph) == _sort_graph(expected)


def _sort_graph(a):
    for k, v in a.items():
        v.sort(
            key=lambda dep_graph: list(dep_graph.keys())[0]
            if len(dep_graph) == 1
            else ""
        )
        for sub_graph in v:
            _sort_graph(sub_graph)
