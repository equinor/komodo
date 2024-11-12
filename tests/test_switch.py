import pytest

from komodo import switch
from komodo.data import Data
from komodo.switch import MIGRATION_WARNING


def test_write_activator_switches(tmpdir):
    prefix = tmpdir / "prefix"
    release = "2022.01.01-py38-rhel7"
    expected_release = "2022.01.01-py38"
    switch.create_activator_switch(Data(), prefix, release)

    actual_bash_activator = prefix / f"{expected_release}/enable"
    bash_source_script_path = "script_path=\"${BASH_SOURCE[0]}\""

    assert (
        actual_bash_activator.read_text(encoding="utf-8").strip()
        == f"""
if [[ $(uname -r) == *el7* ]] ; then
    # Get the full path of the sourced script
    { bash_source_script_path }
    if [[ $script_path == *deprecated-rhel7* ]] ; then
        export KOMODO_ROOT={ prefix }
        KOMODO_RELEASE_REAL={ expected_release }

        source $KOMODO_ROOT/$KOMODO_RELEASE_REAL-rhel7/enable
        export PS1="(${{KOMODO_RELEASE_REAL}}) ${{_PRE_KOMODO_PS1}}"
        export KOMODO_RELEASE=$KOMODO_RELEASE_REAL
    else
        echo "Attention! Your machine is running on an environment 
that is not supported. RHEL7 has been phased out.
From October 2024, komodo versions only support RHEL8.
Please migrate as soon as possible. 

To use the latest stable RHEL7 build use 
source /prog/res/komodo/deprecated-rhel7/enable

If you have any questions or issues - 
contact us on #ert-users on Slack or Equinor's Yammer.
"
    fi
elif [[ $(uname -r) == *el8* ]] ; then
    export KOMODO_ROOT={prefix}
    KOMODO_RELEASE_REAL={expected_release}

    source $KOMODO_ROOT/$KOMODO_RELEASE_REAL-rhel8/enable
    export PS1="(${{KOMODO_RELEASE_REAL}}) ${{_PRE_KOMODO_PS1}}"
    export KOMODO_RELEASE=$KOMODO_RELEASE_REAL
elif [[ $(uname -r) == *el6* ]]; then
    echo -e "{MIGRATION_WARNING}"
else
    echo "Attention! Your machine is running on an environment that is not supported."
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
else if ( `uname -r` =~ *el8* ) then
    setenv KOMODO_ROOT {prefix}
    set KOMODO_RELEASE_REAL = "{expected_release}"

    source $KOMODO_ROOT/$KOMODO_RELEASE_REAL-rhel8/enable.csh
    if ( $?_KOMODO_OLD_PROMPT ) then
        set prompt = "[$KOMODO_RELEASE_REAL] $_KOMODO_OLD_PROMPT"
    endif
    setenv KOMODO_RELEASE $KOMODO_RELEASE_REAL
else if ( `uname -r` =~ *el6* ) then
    echo "Attention! Your machine is running on an environment that is not supported. RHEL6 has been phased out."
    echo "From October 2020, komodo versions only support RHEL7."
    echo "Please migrate as soon as possible. If you have any questions or issues - contact us on #ert-users on Slack or Equinor's Yammer."
else
    echo "Attention! Your machine is running on an environment that is not supported."
endif
""".strip()
    )


def test_write_activator_switches_for_py311(tmpdir):
    prefix = tmpdir / "prefix"
    release = "2024.01.01-py311-rhel8"
    expected_release = "2024.01.01-py311"
    switch.create_activator_switch(Data(), prefix, release)

    actual_bash_activator = prefix / f"{expected_release}/enable"
    assert (
        "Error! Komodo release for Python newer than 3.8 is not available on RHEL7."
        in actual_bash_activator.read_text(encoding="utf-8").strip()
    )

    actual_csh_activator = prefix / f"{expected_release}/enable.csh"
    assert (
        "Error! Komodo release for Python newer than 3.8 is not available on RHEL7."
        in actual_csh_activator.read_text(encoding="utf-8").strip()
    )


def test_write_activator_switches_for_non_matrix_build(tmpdir):
    prefix = tmpdir / "prefix"
    release = "foobar"

    try:
        switch.create_activator_switch(Data(), prefix, release)
    except ValueError as value_error:
        pytest.fail(f"Unexpected ValueError {value_error}")
