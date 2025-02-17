import contextlib
import os
import subprocess
import sys
from typing import List, Optional, Union


@contextlib.contextmanager
def pushd(path):
    prev = os.getcwd()

    if path is not None:
        os.chdir(path)

    yield
    os.chdir(prev)


def shell(cmd: Union[str, List[Optional[str]]], allow_failure: bool = False) -> bytes:
    try:
        cmdlist = cmd.split(" ")
    except AttributeError:
        # was already a list, but to make sure every arg has its own entry,
        # re-join and split
        cmdlist = " ".join(filter(None, cmd)).split(" ")

    prompt = f"[{os.getcwd()}]>"
    print(prompt, " ".join(cmdlist))

    try:
        return subprocess.check_output(tuple(filter(None, cmdlist)))
    except subprocess.CalledProcessError as called_process_error:
        print(called_process_error.output, file=sys.stderr)
        if allow_failure:
            return called_process_error.output
        raise
