from __future__ import print_function
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

def shell(cmd, sudo = False):
    try:
        cmdlist = cmd.split(' ')
    except AttributeError:
        # was already a list, but to make sure every arg has its own entry,
        # re-join and split
        cmdlist = ' '.join(filter(None, cmd)).split(' ')

    if sudo: cmdlist = ['sudo'] + cmdlist

    print('>', ' '.join(cmdlist))

    try: 
        return subprocess.check_output(filter(None, cmdlist))
    except subprocess.CalledProcessError as e:
        print(e.output, file=sys.stderr)
        raise
     
