import sys
from unittest.mock import Mock, patch

import pytest

from komodo.snyk_reporting import snyk_main

if sys.version_info >= (3, 7):
    from snyk.models import Vulnerability

above_py37 = pytest.mark.skipif(
    sys.version_info < (3, 7), reason="requires Python >= 3.7"
)


def _create_result_mock(issue_ids):

    result_mock = Mock()
    result_mock.issues.vulnerabilities = [
        Vulnerability(
            id=issue_id,
            url="some_url",
            title="some_title",
            description="some_description",
            upgradePath="some_upgradePath",
            package="some_package",
            version="some_version",
            severity="some_severity",
            exploitMaturity="some_exploitMaturity",
            isUpgradable="some_isUpgradable",
            isPatchable="some_isPatchable",
            isPinnable="some_isPinnable",
            identifiers="some_identifiers",
            semver="some_semver",
        )
        for issue_id in issue_ids
    ]
    return result_mock


@above_py37
def test_no_api_token():
    with pytest.raises(
        ValueError,
        match=r"No api token given, please set the "
        r"environment variable SNYK_API_TOKEN.",
    ):
        snyk_main(releases={}, repository={}, api_token=None, org_id="some_org_id")


@pytest.mark.skipif(sys.version_info >= (3, 7), reason="requires Python < 3.7")
def test_python36():
    with pytest.raises(RuntimeError):
        snyk_main(releases={}, repository={}, api_token=None, org_id="some_org_id")


@above_py37
@pytest.mark.parametrize(
    "packages,expected_search_string,input_issue_ids,expected_issue_ids",
    [
        (
            {"pyaml": "20.4.0"},
            "pyaml==20.4.0",
            ("some_issue1", "some_issue2"),
            ("some_issue1", "some_issue2"),
        ),
        (
            {"pyaml": "20.4.0"},
            "pyaml==20.4.0",
            ("some_issue1", "some_issue2", "some_issue2"),
            ("some_issue1", "some_issue2"),
        ),
        (
            {"pyaml": "20.4.0", "flask": "1.2.0"},
            "pyaml==20.4.0\nflask==1.2.0",
            ("some_issue1", "some_issue1"),
            ("some_issue1",),
        ),
    ],
)
def test_snyk_reporting(
    packages, expected_search_string, input_issue_ids, expected_issue_ids
):
    releases = {"2025.05.00": packages}
    repositories = {
        k: {
            v: {
                "source": "pypi",
                "make": "pip",
                "maintainer": "someone",
                "depends": [],
            }
        }
        for k, v in packages.items()
    }
    repositories.update(
        {
            "unused_package": {
                "0.4.0": {
                    "source": "pypi",
                    "make": "pip",
                    "maintainer": "someone",
                    "depends": [],
                }
            }
        }
    )
    org_mock = Mock()
    org_mock.test_pipfile.return_value = _create_result_mock(input_issue_ids)
    with patch(
        "komodo.snyk_reporting._get_org", return_value=org_mock
    ) as org_func_mock:
        vulnerabilities = snyk_main(
            releases=releases,
            repository=repositories,
            api_token="some_token",
            org_id="some_org_id",
        )
        org_func_mock.assert_called_once_with("some_token", "some_org_id")
        org_mock.test_pipfile.assert_called_with(expected_search_string)
        vulnerability_ids = [v.id for v in vulnerabilities["2025.05.00"]]
        for vid in expected_issue_ids:
            assert vid in vulnerability_ids
        assert len(vulnerabilities["2025.05.00"]) == len(expected_issue_ids)
