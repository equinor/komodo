#!/usr/bin/env python3

import argparse
import io
import subprocess
import sys

import yaml

from komodo.yaml_file_types import ReleaseFile, RepositoryFile


def run(base_pkgfile, repofile, dot, display_pkg, out):
    with open(base_pkgfile) as bp, open(repofile) as r:
        base_pkgs, repo = yaml.safe_load(bp), yaml.safe_load(r)

    reverse = build_reverse(base_pkgs, repo)

    display_version = base_pkgs[display_pkg]

    if dot:
        _dump_dot(reverse, display_pkg, display_version, out)
    else:
        result = reverse_deps(display_pkg, display_version, reverse)
        yaml.dump(result, out)


def reverse_deps(display_pkg, display_version, reverse):
    return {
        f"{display_pkg}-{display_version}": build_doc(display_pkg, reverse)
        for pkg, version in reverse.items()
    }


def build_reverse(base, repo):
    reverse = {}

    for pkg, version in base.items():
        if pkg not in repo:
            raise SystemExit(f"No package {pkg} in repo")
        if version not in repo[pkg]:
            raise SystemExit(f"No version {version} in package {pkg} in repo")
        repo_version = repo[pkg][version]
        if "depends" in repo_version:
            for dep in repo_version["depends"]:
                if dep not in reverse:
                    reverse[dep] = set()
                reverse[dep].add((pkg, version))

    return reverse


def _dump_dot(reverse, pkg, version, out):
    out.write("digraph G {\n")
    _dump_dot_dep(reverse, pkg, version, out, set())
    out.write("}")


def _dump_dot_dep(reverse, pkg, version, out, seen):
    if pkg in seen:
        return
    _id = pkg.lower().replace("-", "_")
    out.write(f'  {_id} [label="{pkg}-{version}"];\n')
    if pkg in reverse:
        seen.add(pkg)
        for rev_dep, rev_version in reverse[pkg]:
            rev_id = rev_dep.lower().replace("-", "_")
            out.write(f"  {_id} -> {rev_id};\n")
            _dump_dot_dep(reverse, rev_dep, rev_version, out, seen)


def build_doc(pkg, reverse):
    rev_list = []
    if pkg not in reverse:
        return rev_list
    for rev_dep, rev_version in reverse[pkg]:
        rev_list.append({f"{rev_dep}-{rev_version}": build_doc(rev_dep, reverse)})
    return rev_list


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Extracts dependencies from a given set of packages where "
            "versions will be resolved from a complete release file. "
            "Outputs a yaml description. "
            ""
            "Alternatively can write a graph in the dot format. "
            "As a convenience can directly "
            "display the graph as an image, but in that case "
            "needs dot (from Graphwiz) and display "
            "(from ImageMagick) installed."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "base_pkgs",
        type=ReleaseFile(),
        help=(
            "Base Komodo release file where all packages are listed with "
            "wanted versions specified, in YAML format."
        ),
    )
    parser.add_argument(
        "repo",
        type=RepositoryFile(),
        help=(
            "Komodo repository file with all packages listed with dependencies, "
            "in YAML format."
        ),
    )
    parser.add_argument(
        "--pkg",
        "-p",
        help="Package to find reverse dependencies for. If not specified, will prompt.",
    )
    parser.add_argument(
        "--out",
        "-o",
        help=(
            "File to be written with reverse dependencies. "
            "If not specified dump to stdout."
        ),
    )
    parser.add_argument(
        "--dot",
        "-d",
        action="store_true",
        help="Write a dot graph file that can be rendered with dot (from ImageMagick)",
    )
    parser.add_argument(
        "--display_dot",
        "-l",
        action="store_true",
        help=(
            "Try to display graph with dot and display. "
            "You need to have installed these tools, "
            "distibuted with the Graphwiz and ImageMagick packages respectively"
        ),
    )

    args = parser.parse_args()

    if args.pkg:
        pkg = args.pkg
    else:
        pkg = input("pkg:")
        print(f"you entered {pkg}")

    if args.out:
        with open(args.out, "w") as out:
            run(args.base_pkgs, args.repo, args.dot, pkg, out)
    elif args.display_dot:
        try:
            dot_proc = subprocess.Popen(
                ["dot", "-Tpng", "-o"], stdout=subprocess.PIPE, stdin=subprocess.PIPE
            )
            subprocess.Popen(["display"], stdin=dot_proc.stdout)
            out = io.TextIOWrapper(
                dot_proc.stdin,
                encoding="utf-8",
                line_buffering=True,
            )
            run(args.base_pkgs, args.repo, True, pkg, out)
            out.close()
            dot_proc.stdin.close()
        except FileNotFoundError:
            print(
                "When using --display-dot You need to have the "
                "executables dot and display on your path"
            )
    else:
        run(args.base_pkgs, args.repo, args.dot, pkg, sys.stdout)


if __name__ == "__main__":
    main()
