import time
import os
import shutil
import contextlib
import decorator

import komodo


# Will only update links for directories which are older than
# this limit - in seconds.
age_limit = 7200



@contextlib.contextmanager
def _pushd(path):
    cwd0 = os.getcwd()
    os.chdir(path)

    yield

    os.chdir(cwd0)


# The pushd decorator will steal the prefix argument from then
# underlying function and chdir() into that directory, run the
# function and then chdir() back.
def pushd(function):
    def wrapper(prefix):
        with _pushd(prefix):
            function(None)
    return wrapper


@pushd
def update_links(prefix):
    # The first step is to scan the prefix directory and inspect all the
    # directories in the folder. The directory names are split, and a
    # dictionary:
    #
    #     release_list = {"2018.03" : [(1234, "2018.03-1234"),
    #                                  (5678, "2018-03-5678")],
    #                     "2018.10" : [(561, "2018.10.561"),
    #                                  (777, "2018.10-777")]}
    #
    # This is dictionary where the release names like '2018.03' and '2018.10'
    # are used as keys, the values in the dictionary are lists of tuples
    # (timestamp, path_name).
    ts_now = time.mktime( time.localtime() )
    release_list = {}
    for entry in os.listdir(os.getcwd()):
        if os.path.islink(entry):
            continue

        if os.path.isdir(entry):
            release, ts = komodo.split_release_name(entry)
            if not ts:
                continue

            if not release in release_list:
                release_list[release] = []

            release_list[release].append((ts, entry))


    # Go thorugh the datastructure we have assembled; for each releasee (i.e.
    # key in the dict):
    #
    #  1. Sort all the corresponding directories after timestamp.
    #  2. If the newest directory is older than age_limit seconds:
    #     2.a Make sure the release link points to the newest directory.
    #     2.b Remove all the older directories.
    for release,dir_list in release_list.items():
        if os.path.exists(release) and not os.path.islink(release):
            raise IOError("The filesystem entry {} already exists - and is not a symblic link. This must be fixed manually".format(release))


        dir_list = sorted(dir_list, reverse = True)
        ts, root_path = dir_list[0]
        if ts_now - ts < age_limit:
            continue

        if not os.path.exists(release):
            komodo.shell('ln -sf {target} {link}'.format(target=root_path, link=release))

        target_dir = os.readlink(release)
        if target_dir != root_path:
            komodo.shell('ln -sf {target} {link}'.format(target=root_path, link=release))

        for _,root_path in dir_list[1:]:
            komodo.shell('rm -rf {}'.format(root_path))
