import argparse
import os

from ruamel.yaml import YAML

from komodo.yaml_file_types import RepositoryFile


def run(pkgfile, base_pkgfile, repofile, outfile=None):
    with open(pkgfile, encoding="utf-8") as package_file_stream, open(
        base_pkgfile, encoding="utf-8"
    ) as base_package_file_stream, open(
        repofile, encoding="utf-8"
    ) as repository_file_stream:
        yaml = YAML()
        pkgs, base_pkgs, repo = (
            yaml.load(package_file_stream),
            yaml.load(base_package_file_stream),
            yaml.load(repository_file_stream),
        )

    result = _iterate_packages(pkgs, base_pkgs, repo)

    if outfile:
        with open(outfile, "w", encoding="utf-8") as out:
            yaml.dump(result, out)
    else:
        print(yaml.dump(result))


def _iterate_packages(pkgs, base_pkgs, repo):
    dependencies = {}
    for package, version in pkgs.items():
        _extract_dependencies(package, version, base_pkgs, repo, dependencies)
    return dependencies


def _extract_dependencies(package, version, base_pkgs, repofile, dependencies):
    if package not in repofile:
        msg = f"'{package}' not found in 'repo'. This needs to be resolved."
        raise SystemExit(msg)
    if version not in repofile[package]:
        available_versions = list(repofile[package].keys())
        msg = f"Version '{version}' for package '{package}' not found in 'repo'. Available version(s) is: {available_versions}."
        raise SystemExit(
            msg,
        )
    if package not in dependencies:
        dependencies[package] = version

    if "depends" in repofile[package][version]:
        for dependency in repofile[package][version]["depends"]:
            if dependency not in base_pkgs:
                msg = f"'{dependency}' not found in 'base_pkgs'. This needs to be in place in order to pick correct version."
                raise SystemExit(
                    msg,
                )
            version = base_pkgs[dependency]
            _extract_dependencies(
                dependency,
                version,
                base_pkgs,
                repofile,
                dependencies,
            )

    return dependencies


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Extracts dependencies from a given set of packages where "
            "versions will be resolved from a complete release file. "
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "pkgs",
        type=lambda arg: (
            arg if os.path.isfile(arg) else parser.error(f"{arg} is not a file")
        ),
        help="File with packages you want to resolve dependencies for.",
    )
    parser.add_argument(
        "base_pkgs",
        type=lambda arg: (
            arg if os.path.isfile(arg) else parser.error(f"{arg} is not a file")
        ),
        help="Base file where all packages are listed with wanted versions specified.",
    )
    parser.add_argument(
        "repo",
        type=RepositoryFile(),
        help="Repository file with all packages listed with dependencies.",
    )
    parser.add_argument(
        "--out",
        "-o",
        help=(
            "File to be written with resolved dependencies. "
            "If not specified dump to stdout."
        ),
    )

    args = parser.parse_args()
    run(args.pkgs, args.base_pkgs, args.repo, args.out)


if __name__ == "__main__":
    main()
