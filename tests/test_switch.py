import pytest

from komodo import switch
from komodo.data import Data


@pytest.mark.parametrize(
    "release, expected_release, custom_coord",
    [
        ("2024.03.03-py311-rhel8", "2024.03.03-py311", ""),
        ("2024.04.04-py312-rhel8", "2024.04.04-py312", ""),
        ("2025.05.05-py312-rhel9", "2025.05.05-py312", ""),
        ("2025.05.05-py312-rhel9-numpy1", "2025.05.05-py312", "numpy1"),
    ],
)
def test_write_activator_switches(tmpdir, release, expected_release, custom_coord):
    prefix = tmpdir / "prefix"
    switch.create_activator_switch(Data(), prefix, release)
    custom_coordinate = ("-" + custom_coord) if custom_coord else ""

    actual_bash_activator = prefix / f"{expected_release}/enable"

    assert (
        actual_bash_activator.read_text(encoding="utf-8").strip()
        == f"""
CUSTOM_COORDINATE="{custom_coordinate}"


if [[ $(uname -r) == *el8* ]] || [[ $(uname -r) == *el9* ]] ; then
    export KOMODO_ROOT={prefix}
    rhel_version_number=$(uname -r | grep -oP 'el\\K[0-9]')
    KOMODO_RELEASE_REAL={expected_release}-rhel$rhel_version_number$CUSTOM_COORDINATE

    source $KOMODO_ROOT/$KOMODO_RELEASE_REAL/enable
    export PS1="(${{KOMODO_RELEASE_REAL}}) ${{_PRE_KOMODO_PS1}}"
    export KOMODO_RELEASE=$KOMODO_RELEASE_REAL
else
    echo "Attention! Your machine is running on an environment that is not supported."
fi
""".strip()
    )

    actual_csh_activator = prefix / f"{expected_release}/enable.csh"
    assert (
        actual_csh_activator.read_text(encoding="utf-8").strip()
        == f"""
set CUSTOM_COORDINATE="{custom_coordinate}"


set rhel_version_number = `uname -r | grep -oP 'el\\K[8-9]'`
if ( $status == 0 ) then
    setenv KOMODO_ROOT {prefix}
    set KOMODO_RELEASE_REAL = "{expected_release}"-rhel$rhel_version_number$CUSTOM_COORDINATE

    source $KOMODO_ROOT/$KOMODO_RELEASE_REAL/enable.csh
    if ( $?_KOMODO_OLD_PROMPT ) then
        set prompt = "[$KOMODO_RELEASE_REAL] $_KOMODO_OLD_PROMPT"
    endif
    setenv KOMODO_RELEASE $KOMODO_RELEASE_REAL
else
    echo "Attention! Your machine is running on an environment that is not supported."
endif
""".strip()
    )


def test_write_activator_switches_for_non_matrix_build(tmpdir):
    prefix = tmpdir / "prefix"
    release = "foobar"

    try:
        switch.create_activator_switch(Data(), prefix, release)
    except ValueError as value_error:
        pytest.fail(f"Unexpected ValueError {value_error}")


@pytest.mark.parametrize(
    "release, base_ver, py_ver, rhel_ver, custom_ver",
    [
        ("2024.03.03-py311-rhel8", "2024.03.03-py311", "py311", "rhel8", ""),
        ("2024.04.04-py312-rhel8", "2024.04.04-py312", "py312", "rhel8", ""),
        ("2025.05.05-py312-rhel9", "2025.05.05-py312", "py312", "rhel9", ""),
        (
            "2025.05.05-py312-rhel9-numpy1",
            "2025.05.05-py312",
            "py312",
            "rhel9",
            "numpy1",
        ),
        (
            "bleeding-20250204-1434-py38-rhel9",
            "bleeding-20250204-1434-py38",
            "py38",
            "rhel9",
            "",
        ),
        (
            "bleeding-20250204-1434-py311-rhel8-numpy1",
            "bleeding-20250204-1434-py311",
            "py311",
            "rhel8",
            "numpy1",
        ),
    ],
)
def test_extract_version_strings(release, base_ver, py_ver, rhel_ver, custom_ver):
    base, py, rhel, custom_cord = switch.extract_versions(release)
    assert base == base_ver
    assert py == py_ver
    assert rhel == rhel_ver
    assert custom_cord == custom_ver
