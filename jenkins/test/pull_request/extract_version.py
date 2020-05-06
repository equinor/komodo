#!/usr/bin/env python
import yaml  # pip install PyYaml
import os
import sys
import re


def main(release_root, package):
    pattern = re.compile(r"^([^+]+)")

    release_name = os.path.basename(os.path.realpath(release_root))
    versions_path = os.path.join(release_root, release_name)

    with open(versions_path) as f:
        versions = yaml.safe_load(f)

    if package not in versions:
        sys.stderr.write("Package '{}' does not exist in {}", package, versions_path)
        sys.exit(1)

    version = versions[package]["version"]
    matchdata = pattern.match(version)
    if not matchdata:
        sys.stderr.write("Version for package '{}' is not properly formatted (version={})", package, repr(version))
        sys.exit(2)

    print(matchdata[1])


if __name__ == "__main__":
    main(release_root=sys.argv[1], package=sys.argv[2])
