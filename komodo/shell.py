import contextlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Generator, Mapping, Optional, Protocol, Union


class _Run(Protocol):
    def __call__(
        self,
        executable: Union[str, Path],
        *args: Union[str, Path],
        setenv: Optional[Mapping[str, str]] = None,
        cwd: Union[None, str, Path] = None,
        check: bool = True,
    ) -> bytes:
        ...


def run(
    executable: Union[str, Path],
    *args: Union[str, Path, None],
    setenv: Optional[Mapping[str, str]] = None,
    cwd: Union[None, str, Path] = None,
    check: bool = True,
) -> bytes:
    if cwd is None:
        cwd = os.getcwd()

    env: Optional[Mapping[str, str]] = None
    if setenv is not None:
        env = {**os.environ, **setenv}

    cmd = [executable]
    cmd.extend(x for x in args if x is not None)

    try:
        print(f"[{cwd}]> {' '.join(map(str, cmd))}")
        return subprocess.check_output(cmd, env=env, cwd=cwd)
    except subprocess.CalledProcessError as e:
        print(e.output, file=sys.stderr)
        if not check:
            return e.output
        raise


@contextlib.contextmanager
def run_env(
    *, setenv: Optional[Mapping[str, str]] = None, cwd: Union[None, str, Path] = None
) -> Generator[_Run, None, None]:
    def fn(executable: Union[str, Path], *args: Union[str, Path]) -> bytes:
        return run(executable, *args, setenv=setenv, cwd=cwd)

    yield fn
