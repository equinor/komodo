import os
from komodo.deployed import fetch_non_deployed


def _create_deployed_releases(releases, root=""):
    root = os.path.realpath(root)
    for release in releases:
        os.makedirs(os.path.join(root, release))


def _create_links(links, root=""):
    root = os.path.realpath(root)
    for (src, target) in links:
        os.symlink(
            os.path.join(root, src),
            os.path.join(root, target),
        )


def _create_release_files(release_files, root=""):
    root = os.path.realpath(root)
    for release_file in release_files:
        release_file = os.path.join(root, release_file)
        with open(release_file, "w") as f:
            f.write("This is a release!")


def test_non_deployed_empty(tmpdir):
    with tmpdir.as_cwd():
        install_root = "install_root"
        release_folder = "release_folder"
        os.makedirs(install_root)
        os.makedirs(release_folder)

        _create_deployed_releases(
            ("2019.12.02-py36", "2022.02.01-py36"), root=install_root
        )
        _create_links(
            (("2019.12.02-py36", "2019.12"), ("2022.02.01-py36", "2022.02"),),
            root=install_root,
        )

        non_deployed = fetch_non_deployed(install_root, release_folder)
        assert len(non_deployed) == 0, non_deployed


def test_non_deployed(tmpdir):
    with tmpdir.as_cwd():
        install_root = "install_root"
        release_folder = "release_folder"
        os.makedirs(install_root)
        os.makedirs(release_folder)

        deployed_releases = ("2019.12.02-py36", "2022.02.01-py36")
        _create_deployed_releases(deployed_releases, root=install_root)
        non_deployed_releases = ("2020.02.01-py36", "2040.05.07-py36")
        release_files = tuple(
            fn + ".yml" for fn in deployed_releases + non_deployed_releases
        )
        _create_release_files(
            release_files, root=release_folder,
        )
        non_deployed = fetch_non_deployed(install_root, release_folder)
        assert sorted(non_deployed_releases) == sorted(non_deployed)


def test_pattern_replace(tmpdir):
    with tmpdir.as_cwd():
        install_root = "install_root"
        release_folder = "release_folder"
        os.makedirs(install_root)
        os.makedirs(release_folder)

        deployed_releases = ("2019.12.02-py36", "2022.02.01-py36")
        _create_deployed_releases(deployed_releases, root=install_root)
        non_deployed_releases = ("2020.02.01-py36", "2040.05.07-py36")
        release_files = tuple(
            fn + ".yml" for fn in deployed_releases + non_deployed_releases
        )
        _create_release_files(
            release_files, root=release_folder,
        )
        non_deployed = fetch_non_deployed(install_root, release_folder, pattern="-py36$", remove_pattern=True)
        assert sorted([n[:-5] for n in non_deployed_releases]) == sorted(non_deployed)


def test_links_ignored(tmpdir):
    with tmpdir.as_cwd():
        install_root = "install_root"
        release_folder = "release_folder"
        os.makedirs(install_root)
        os.makedirs(release_folder)

        deployed_releases = ("2019.12-py36", "2022.02-py36")
        _create_deployed_releases(deployed_releases, root=install_root)
        _create_links(
            (
                ("2019.12-py36", "2020.02.01-py36"),
                ("2022.02-py36", "2040.05.07-py36"),
            ),
            root=install_root,
        )
        non_deployed_releases = ("2020.02.01-py36", "2040.05.07-py36")
        release_files = (
            tuple(fn + ".yml" for fn in deployed_releases + non_deployed_releases)
        )
        _create_release_files(
            release_files, root=release_folder,
        )
        non_deployed = fetch_non_deployed(install_root, release_folder)
        assert len(non_deployed) == 0, non_deployed
