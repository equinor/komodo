import pytest

from komodo import switch
from komodo.data import Data


@pytest.mark.parametrize(
    "release, expected_release",
    [
        ("2024.03.03-py311-rhel8", "2024.03.03-py311"),
        ("2024.04.04-py312-rhel8", "2024.04.04-py312"),
        ("2025.05.05-py312-rhel9", "2025.05.05-py312"),
        ("2025.05.05-py312-rhel9-numpy1", "2025.05.05-py312"),
    ],
)
def test_write_activator_switches(tmpdir, release, expected_release):
    prefix = tmpdir / "prefix"
    switch.create_activator_switch(Data(), prefix, release)

    actual_bash_activator = prefix / f"{expected_release}/enable"

    assert (
        actual_bash_activator.read_text(encoding="utf-8").strip()
        == f"""
if [[ $(uname -r) == *el8* ]] || [[ $(uname -r) == *el9* ]] ; then
    export KOMODO_ROOT={prefix}
    KOMODO_RELEASE_REAL={expected_release}

    rhel_version_number=$(uname -r | grep -oP 'el\\K[0-9]')
    source $KOMODO_ROOT/$KOMODO_RELEASE_REAL-rhel$rhel_version_number/enable
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
if ( `uname -r` =~ *el8* ) || ( `uname -r` =~ *el9* ) then
    setenv KOMODO_ROOT {prefix}
    set KOMODO_RELEASE_REAL = "{expected_release}"

    set rhel_version_number=`uname -r | grep -oP 'el\\K[0-9]'`
    source $KOMODO_ROOT/$KOMODO_RELEASE_REAL-rhel$rhel_version_number/enable.csh
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
