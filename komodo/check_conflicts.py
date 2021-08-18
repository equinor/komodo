import argparse
import pathlib
import subprocess
import sys
import tempfile
import platform
import venv
import contextlib

import yaml

from komodo.check_up_to_date_pypi import get_pypi_packages
from komodo.package_version import strip_version


@contextlib.contextmanager
def temporary_environment():
    class EnvBuilder(venv.EnvBuilder):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.context = None

        def post_setup(self, context):
            self.context = context

    with tempfile.TemporaryDirectory() as tmp_dir:
        builder = EnvBuilder(with_pip=True)
        builder.create(str(tmp_dir))
        context = builder.context
        yield context.env_exe


def main():
    parser = argparse.ArgumentParser(
        description="Checks if pypi packages are compatible"
    )
    parser.add_argument(
        "release_file",
        type=lambda arg: arg
        if pathlib.Path(arg).is_file()
        else parser.error("{} is not a file".format(arg)),
        help="Release file you would like to check dependencies on.",
    )
    parser.add_argument(
        "repository_file",
        type=lambda arg: arg
        if pathlib.Path(arg).is_file()
        else parser.error("{} is not a file".format(arg)),
        help="Repository file where the source of the packages is found",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=False,
        help="Output file where requirements are written",
    )
    parser.add_argument(
        "--try-pip",
        action="store_true",
        help="If given, will try to install packages and check validity. Note that "
        "creates a virtual environment and is quite slow",
    )

    args = parser.parse_args()
    with open(args.release_file) as fin:
        releases = yaml.safe_load(fin)
    with open(args.repository_file) as fin:
        repository = yaml.safe_load(fin)

    pypi_packages = get_pypi_packages(releases, repository)

    requirements = []
    for package in pypi_packages:
        if package == "opm" and platform.system() == "Darwin":
            print("Found opm, which has no osx source (as of 08.2021)")
            continue
        version = strip_version(releases[package])
        requirements.append(f"{package}=={version}")

    if args.output_file:
        with open(args.output_file, "w") as fout:
            fout.write("\n".join(requirements) + "\n")

    if args.try_pip:
        print("Checking dependencies, this is usually slow")
        with temporary_environment() as current_python:
            upgrade_pip = subprocess.run(
                [
                    current_python,
                    "-m",
                    "pip",
                    "install",
                    "pip",
                    "-U",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if upgrade_pip.returncode == 1:
                sys.exit(
                    upgrade_pip.stderr.decode("utf-8")
                    + "\n Upgrading pip failed"
                )
            install = subprocess.run(
                [
                    current_python,
                    "-m",
                    "pip",
                    "install",
                    *requirements,
                    "--no-deps",
                    "--force-reinstall",  # Probably not needed
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if install.returncode == 1:
                sys.exit(
                    install.stderr.decode("utf-8")
                    + "\n Installation of packages failed"
                )
            result = subprocess.run(
                [current_python, "-m", "pip", "check"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode == 1:
                sys.exit(result.stdout.decode("utf-8"))
            else:
                print("Everything is awesome!")
