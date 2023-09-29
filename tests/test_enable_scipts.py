import json
from pathlib import Path

from komodo.cli import create_enable_scripts
from komodo.shell import shell


def _load_envs():
    with open("pre_source.env") as pre:
        pre_env = json.loads(pre.read())
    with open("sourced.env") as sourced:
        sourced_env = json.loads(sourced.read())
    with open("post_disable.env") as post:
        post_env = json.loads(post.read())

    return pre_env, sourced_env, post_env


TEST_SCRIPT_SIMPLE = """\
{set_envs}
python -c 'import os, json; print(json.dumps(dict(os.environ)))' > pre_source.env
source {enable_path}
python -c 'import os, json; print(json.dumps(dict(os.environ)))' > sourced.env
disable_komodo
python -c 'import os, json; print(json.dumps(dict(os.environ)))' > post_disable.env
"""


CLEAN_BASH_ENV = """\
unset MANPATH
unset LD_LIBRARY_PATH
"""


def test_enable_bash_nopresets(tmpdir):
    with tmpdir.as_cwd():
        Path("bleeding").mkdir()
        create_enable_scripts(komodo_prefix="prefix", komodo_release="bleeding")
        with open("test_enable.sh", "w") as test_file:
            test_file.write(
                TEST_SCRIPT_SIMPLE.format(
                    set_envs=CLEAN_BASH_ENV,
                    enable_path="bleeding/enable",
                ),
            )

        shell(["bash test_enable.sh"])
        pre_env, sourced_env, post_env = _load_envs()

        assert "LD_LIBRARY_PATH" not in pre_env
        assert sourced_env["LD_LIBRARY_PATH"] == "prefix/lib:prefix/lib64"
        assert "MANPATH" not in pre_env
        assert sourced_env["MANPATH"] == "prefix/share/man:"
        assert pre_env == post_env


CLEAN_CSH_ENV = """\
unsetenv MANPATH
unsetenv LD_LIBRARY_PATH
"""


def test_enable_csh_no_presets(tmpdir):
    with tmpdir.as_cwd():
        Path("bleeding").mkdir()
        create_enable_scripts(komodo_prefix="prefix", komodo_release="bleeding")
        with open("test_enable.sh", "w") as test_file:
            test_file.write(
                TEST_SCRIPT_SIMPLE.format(
                    set_envs=CLEAN_CSH_ENV,
                    enable_path="bleeding/enable.csh",
                ),
            )

        shell(["csh test_enable.sh"])
        pre_env, sourced_env, post_env = _load_envs()

        assert "LD_LIBRARY_PATH" not in pre_env
        assert sourced_env["LD_LIBRARY_PATH"] == "prefix/lib:prefix/lib64"
        assert "MANPATH" not in pre_env
        assert sourced_env["MANPATH"] == "prefix/share/man:"
        assert pre_env == post_env


BASH_ENVS = """\
export LD_LIBRARY_PATH=/some/path
export MANPATH=/some/man/path
"""


def test_enable_bash_with_presets(tmpdir):
    with tmpdir.as_cwd():
        Path("bleeding").mkdir()
        create_enable_scripts(komodo_prefix="prefix", komodo_release="bleeding")
        Path("test_enable.sh").write_text(
            TEST_SCRIPT_SIMPLE.format(
                set_envs=BASH_ENVS,
                enable_path="bleeding/enable",
            ),
            encoding="utf-8",
        )

        shell(["bash test_enable.sh"])
        pre_env, sourced_env, post_env = _load_envs()
        assert pre_env["LD_LIBRARY_PATH"] == "/some/path"
        assert sourced_env["LD_LIBRARY_PATH"] == "prefix/lib:prefix/lib64:/some/path"
        assert pre_env["MANPATH"] == "/some/man/path"
        assert sourced_env["MANPATH"] == "prefix/share/man:/some/man/path"
        assert pre_env == post_env


CSH_ENVS = """\
setenv LD_LIBRARY_PATH /some/path
setenv MANPATH /some/man/path
"""


def test_enable_csh_with_presets(tmpdir):
    with tmpdir.as_cwd():
        Path("bleeding").mkdir()
        create_enable_scripts(komodo_prefix="prefix", komodo_release="bleeding")
        Path("test_enable.sh").write_text(
            TEST_SCRIPT_SIMPLE.format(
                set_envs=CSH_ENVS,
                enable_path="bleeding/enable.csh",
            ),
            encoding="utf-8",
        )

        shell(["csh test_enable.sh"])
        pre_env, sourced_env, post_env = _load_envs()

        assert pre_env["LD_LIBRARY_PATH"] == "/some/path"
        assert sourced_env["LD_LIBRARY_PATH"] == "prefix/lib:prefix/lib64:/some/path"
        assert pre_env["MANPATH"] == "/some/man/path"
        assert sourced_env["MANPATH"] == "prefix/share/man:/some/man/path"
        assert pre_env == post_env
