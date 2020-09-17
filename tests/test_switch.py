import os

import pytest  # noqa
from komodo import switch
from komodo.data import Data
from komodo.switch import MIGRATION_WARNING


def test_write_activator_switches(tmpdir):
    tmpdir = str(tmpdir)  # XXX: python2 support
    prefix = os.path.join(tmpdir, "prefix")
    release = "2020.01.01-py27-rhel6"
    expected_release = "2020.01.01-py27"
    switch.create_activator_switch(Data(), prefix, release)

    actual_bash_activator = os.path.join(prefix, "{}/enable".format(expected_release))
    with open(actual_bash_activator) as actual:
        expected = """if [[ $(uname -r) == *el7* ]] ; then
    export KOMODO_ROOT={prefix}
    KOMODO_RELEASE_REAL={release}

    source $KOMODO_ROOT/$KOMODO_RELEASE_REAL-rhel7/enable
    export PS1="(${{KOMODO_RELEASE_REAL}}) ${{_PRE_KOMODO_PS1}}"
    export KOMODO_RELEASE=$KOMODO_RELEASE_REAL
else
    echo "{migration_warning}"
fi
""".format(
            release=expected_release,
            prefix=prefix,
            migration_warning=MIGRATION_WARNING,
        )

        assert actual.read() == expected

    actual_csh_activator = os.path.join(
        prefix, "{}/enable.csh".format(expected_release)
    )
    with open(actual_csh_activator) as actual:
        expected = """if ( `uname -r` =~ *el7* ) then
    setenv KOMODO_ROOT {prefix}
    set KOMODO_RELEASE_REAL = "{release}"

    source $KOMODO_ROOT/$KOMODO_RELEASE_REAL-rhel7/enable.csh
    set prompt = "[$KOMODO_RELEASE_REAL] $prompt"
    setenv KOMODO_RELEASE $KOMODO_RELEASE_REAL
else
    echo "{migration_warning}"
endif
""".format(
            release=expected_release,
            prefix=prefix,
            migration_warning=MIGRATION_WARNING,
        )
        assert actual.read() == expected


def test_write_activator_switches_for_non_matrix_build(tmpdir):
    tmpdir = str(tmpdir)  # XXX: python2 support
    prefix = os.path.join(tmpdir, "prefix")
    release = "foobar"

    try:
        switch.create_activator_switch(Data(), prefix, release)
    except ValueError as e:
        pytest.fail("Unexpected ValueError " + e)
