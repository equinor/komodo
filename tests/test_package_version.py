import sys
from subprocess import CalledProcessError
from unittest.mock import patch

import pytest

from komodo.package_version import latest_pypi_version


@pytest.mark.parametrize(
    "cmd_stderr,expected_version",
    [
        (
            """ERROR: Could not find a version that satisfies the requirement equinor_libres== (from versions: 3.3.1a9, 7.2.0b0, 7.2.0rc0, 8.0.0rc0, 8.0.0, 8.0.1, 8.1.0rc0, 9.0.0b0, 9.0.0b1)
    ERROR: No matching distribution found for equinor_libres==""",
            "9.0.0b1",
        ),
        (
            """ERROR: Could not find a version that satisfies the requirement equinor_libres== (from versions: 0.1.0)
ERROR: No matching distribution found for equinor_libres==""",
            "0.1.0",
        ),
        (
            """ERROR: Could not find a version that satisfies the requirement equinor_libres== (from versions: none)
ERROR: No matching distribution found for equinor_libres==""",
            None,
        ),
    ],
)
def test_latest_pypi_version(cmd_stderr, expected_version):
    def _raise(*args, **kwargs):
        raise CalledProcessError(
            1, "", stderr=bytes(cmd_stderr.encode(sys.getfilesystemencoding()))
        )

    with patch("subprocess.check_output") as mock_check_output:
        mock_check_output.side_effect = _raise
        assert latest_pypi_version("equinor_libres") == expected_version
