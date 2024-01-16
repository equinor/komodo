import contextlib
import os
import subprocess
import sys


@contextlib.contextmanager
def pushd(path):
    prev = os.getcwd()

    if path is not None:
        os.chdir(path)

    yield
    os.chdir(prev)


def shell(cmd: str, sudo=False, allow_failure=False) -> bytes:
    try:
        cmdlist = cmd.split(" ")
    except AttributeError:
        # was already a list, but to make sure every arg has its own entry,
        # re-join and split
        cmdlist = " ".join(filter(None, cmd)).split(" ")

    if sudo:
        cmdlist = ["sudo", *cmdlist]

    prompt = f"[{os.getcwd()}]>"
    print(prompt, " ".join(cmdlist))

    try:
        return subprocess.check_output(tuple(filter(None, cmdlist)))
    except subprocess.CalledProcessError as e:
        print(e.output.decode("utf-8", "replace"), file=sys.stderr)
        if allow_failure:
            return e.output
        raise
