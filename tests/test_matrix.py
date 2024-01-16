import pytest

from komodo import matrix


def test_format_matrix():
    assert matrix.format_release("base", "py27") == "base-py27"


@pytest.mark.parametrize(
    ("test_input", "expected"),
    [
        ("1970.12.01-py38", "1970.12.01"),
        ("1970.12.rc0-foo-py38", "1970.12.rc0-foo"),
        ("1970.12.03", "1970.12.03"),
        (matrix.format_release("1970.12.04", "py38"), "1970.12.04"),
        ("1970.12.05-py27", "1970.12.05"),  # outside matrix
    ],
)
def test_get_matrix_base(test_input, expected):
    assert matrix.get_matrix_base(test_input) == expected
