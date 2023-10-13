import pytest

from komodo import switch
from komodo.data import Data
from komodo.switch import MIGRATION_WARNING


def test_write_activator_switches(tmpdir):
    prefix = tmpdir / "prefix"
    release = "2020.01.01-py27-rhel6"
    expected_release = "2020.01.01-py27"
    switch.create_activator_switch(Data(), prefix, release)

    actual_bash_activator = prefix / f"{expected_release}/enable"
    assert (
        actual_bash_activator.read_text(encoding="utf-8").strip()
        == f"""
if [[ $(uname -r) == *el7* ]] ; then
    export KOMODO_ROOT={prefix}
    KOMODO_RELEASE_REAL={expected_release}

    source $KOMODO_ROOT/$KOMODO_RELEASE_REAL-rhel7/enable
    export PS1="(${{KOMODO_RELEASE_REAL}}) ${{_PRE_KOMODO_PS1}}"
    export KOMODO_RELEASE=$KOMODO_RELEASE_REAL
else
    echo -e "{MIGRATION_WARNING}"
fi
""".strip()
    )

    actual_csh_activator = prefix / f"{expected_release}/enable.csh"
    assert (
        actual_csh_activator.read_text(encoding="utf-8").strip()
        == f"""
if ( `uname -r` =~ *el7* ) then
    setenv KOMODO_ROOT {prefix}
    set KOMODO_RELEASE_REAL = "{expected_release}"

    source $KOMODO_ROOT/$KOMODO_RELEASE_REAL-rhel7/enable.csh
    if ( $?_KOMODO_OLD_PROMPT ) then
        set prompt = "[$KOMODO_RELEASE_REAL] $_KOMODO_OLD_PROMPT"
    endif
    setenv KOMODO_RELEASE $KOMODO_RELEASE_REAL
else
    echo -e "{MIGRATION_WARNING}"
endif
""".strip()
    )


def test_write_activator_switches_for_non_matrix_build(tmpdir):
    prefix = tmpdir / "prefix"
    release = "foobar"

    try:
        switch.create_activator_switch(Data(), prefix, release)
    except ValueError as e:
        pytest.fail("Unexpected ValueError " + e)
