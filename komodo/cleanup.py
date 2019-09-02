#!/usr/bin/env python
from __future__ import print_function

import logging
import yaml as yml

def cleanup(repofile, releasefiles):
    with open(repofile, 'r') as r:
        repo = yml.safe_load(r)
    rels = []
    for fname in releasefiles:
        with open(fname, 'r') as f:
            rels.append(yml.safe_load(f))

    if not isinstance(repo, dict):
        raise ValueError('Malformed package file: %s ' % str(type(repo)))
    for rel in rels:
        if not isinstance(rel, dict):
            raise ValueError('Malformed repository file: %s' % str(type(rel)))

    registered_versions = []
    for pkg in repo:
        for v in repo[pkg]:
            registered_versions.append((pkg,v))

    seen_versions = set()
    for rel in rels:
        for pkg in rel:
            seen_versions.add((pkg, rel[pkg]))

    seen_all = True
    for ver in registered_versions:
        if ver not in seen_versions:
            if seen_all:
                print('unused:')
                seen_all = False
            print('  - %s: %s' % ver)
    if seen_all:
        print('ok')



if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        exit('usage: komodo.cleanup repo.yml rel1.yml rel2.yml ... reln.yml')

    repo = sys.argv[1]
    releases = sys.argv[2:]
    cleanup(repo, releases)
