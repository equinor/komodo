import os

import pytest

from komodo import switch
from komodo.data import Data
from komodo.switch import MIGRATION_WARNING


def test_write_activator_switches(tmpdir):
    tmpdir = str(tmpdir)  # XXX: python2 support
    prefix = os.path.join(tmpdir, "prefix")
    release = "2020.01.01-py27-rhel6"
    expected_release = "2020.01.01-py27"
    switch.create_activator_switch(Data(), prefix, release)

    actual_bash_activator = os.path.join(prefix, f"{expected_release}/enable")
    with open(actual_bash_activator) as actual:
        expected = f"""if [[ $(uname -r) == *el7* ]] ; then
    export KOMODO_ROOT={prefix}
    KOMODO_RELEASE_REAL={expected_release}

    source $KOMODO_ROOT/$KOMODO_RELEASE_REAL-rhel7/enable
    export PS1="(${{KOMODO_RELEASE_REAL}}) ${{_PRE_KOMODO_PS1}}"
    export KOMODO_RELEASE=$KOMODO_RELEASE_REAL
else
    echo -e "{MIGRATION_WARNING}"
fi
"""

        assert actual.read() == expected

    actual_csh_activator = os.path.join(
        prefix,
        f"{expected_release}/enable.csh",
    )
    with open(actual_csh_activator) as actual:
        expected = f"""if ( `uname -r` =~ *el7* ) then
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
"""
        assert actual.read() == expected


def test_write_activator_switches_for_non_matrix_build(tmpdir):
    tmpdir = str(tmpdir)  # XXX: python2 support
    prefix = os.path.join(tmpdir, "prefix")
    release = "foobar"

    try:
        switch.create_activator_switch(Data(), prefix, release)
    except ValueError as e:
        pytest.fail("Unexpected ValueError " + e)
