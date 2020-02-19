import argparse
import os
import sys

import yaml


def run(pkgfile, base_pkgfile, repofile, outfile=None):
    with open(pkgfile) as p, open(base_pkgfile) as bp, open(repofile) as r:
        pkgs, base_pkgs, repo = yaml.safe_load(p), yaml.safe_load(bp), yaml.safe_load(r)

    result = _iterate_packages(pkgs, base_pkgs, repo)

    if outfile:
        with open(outfile, "w") as out:
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
        raise SystemExit(
            "'{}' not found in 'repo'. This needs to be resolved.".format(package)
        )
    if version not in repofile[package]:
        available_versions = list(repofile[package].keys())
        raise SystemExit(
            "Version '{}' for package '{}' not found in 'repo'. Available version(s) is: {}.".format(
                version, package, available_versions
            )
        )
    if package not in dependencies:
        dependencies[package] = version

    if "depends" in repofile[package][version]:
        for dependency in repofile[package][version]["depends"]:
            if not dependency in base_pkgs:
                raise SystemExit(
                    "'{}' not found in 'base_pkgs'. This needs to be in place in order to pick correct version.".format(
                        dependency
                    )
                )
            version = base_pkgs[dependency]
            _extract_dependencies(
                dependency, version, base_pkgs, repofile, dependencies
            )

    return dependencies


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Extracts dependencies from a given set of packages where "
            "versions will be resolved from a complete release file. "
        )
    )
    parser.add_argument(
        "pkgs",
        type=lambda arg: arg
        if os.path.isfile(arg)
        else parser.error("{} is not a file".format(arg)),
        help="File with packages you want to resolve dependencies for.",
    )
    parser.add_argument(
        "base_pkgs",
        type=lambda arg: arg
        if os.path.isfile(arg)
        else parser.error("{} is not a file".format(arg)),
        help="Base file where all packages are listed with wanted versions specified.",
    )
    parser.add_argument(
        "repo",
        type=lambda arg: arg
        if os.path.isfile(arg)
        else parser.error("{} is not a file".format(arg)),
        help="Repository file with all packages listed with dependencies.",
    )
    parser.add_argument(
        "--out",
        "-o",
        help="File to be written with resolved dependencies. If not specified dump to stdout.",
    )

    args = parser.parse_args()
    run(args.pkgs, args.base_pkgs, args.repo, args.out)


if __name__ == "__main__":
    main()
