import pytest

from komodo import matrix


@pytest.mark.parametrize(
    ("base", "rhel", "python", "other", "expected"),
    [
        ("base", "rhel6", "py27", None, "base-py27-rhel6"),
        ("base", "rhel6", "py27", "numpy1", "base-py27-rhel6-numpy1"),
    ],
)
def test_format_matrix(base, rhel, python, other, expected):
    assert matrix.format_release(base, rhel, python, other) == expected


@pytest.mark.parametrize(
    ("test_input", "expected"),
    [
        ("1970.12.01-py38-rhel7", "1970.12.01"),
        ("1970.12.rc0-foo-py38-rhel7", "1970.12.rc0-foo"),
        ("1970.12.03", "1970.12.03"),
        (matrix.format_release("1970.12.04", "rhel7", "py38"), "1970.12.04"),
        (matrix.format_release("1990.06.04", "rhel9", "py38", "numpy2"), "1990.06.04"),
        ("1970.12.05-rhel8-py27", "1970.12.05-rhel8-py27"),  # outside matrix
        ("2025.02.00-py311-rhel9-numpy2", "2025.02.00"),
    ],
)
def test_get_matrix_base(test_input, expected):
    assert matrix.get_matrix_base(test_input) == expected


@pytest.mark.parametrize(
    ("rhel_ver", "py_ver", "other_ver", "expected_yield"),
    [
        (
            ["8"],
            ["38", "311"],
            None,
            [("rhel8", "py38", None), ("rhel8", "py311", None)],
        ),
        (
            ["8", "9"],
            ["311"],
            {"numpy": ["1", "2"]},
            [
                ("rhel8", "py311", "numpy1"),
                ("rhel8", "py311", "numpy2"),
                ("rhel9", "py311", "numpy1"),
                ("rhel9", "py311", "numpy2"),
            ],
        ),
    ],
)
def test_get_matrix(rhel_ver, py_ver, other_ver, expected_yield):
    yielded = list(matrix.get_matrix(rhel_ver, py_ver, other_ver))
    assert yielded == expected_yield
