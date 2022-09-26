import os

from komodo.deployed import fetch_non_deployed


def _create_links(links, root=""):
    root = os.path.realpath(root)
    for (src, target) in links:
        os.symlink(
            os.path.join(root, src),
            os.path.join(root, target),
            target_is_directory=True,
        )


def test_non_deployed_empty(tmpdir):
    with tmpdir.as_cwd():
        install_root = "install_root"
        release_folder = "release_folder"
        os.makedirs(release_folder)

        # partially deployed, but this currently means it is deployed
        os.makedirs(os.path.join(install_root, "2019.12.02-py38-rhel7/root"))
        os.makedirs(os.path.join(install_root, "2022.02.01-py38-rhel7/root"))

        _create_links(
            (
                ("2019.12.02-py38-rhel7", "2019.12"),
                ("2022.02.01-py38-rhel7", "2022.02"),
            ),
            root=install_root,
        )

        non_deployed = fetch_non_deployed(install_root, release_folder)
        assert len(non_deployed) == 0, non_deployed


def test_non_deployed(tmpdir):
    with tmpdir.as_cwd():
        install_root = "install_root"
        release_folder = "release_folder"
        os.makedirs(release_folder)

        # Fully deployed
        os.makedirs(os.path.join(install_root, "2019.11.05-py38-rhel7/root"))

        # Create matrix files
        open(os.path.join(release_folder, "2019.11.05.yml"), "a").close()
        open(os.path.join(release_folder, "2019.12.02.yml"), "a").close()

        expected = ("2019.12.02",)
        actual = fetch_non_deployed(install_root, release_folder)
        assert sorted(expected) == sorted(actual)


def test_links_ignored(tmpdir):
    with tmpdir.as_cwd():
        install_root = "install_root"
        release_folder = "release_folder"
        os.makedirs(release_folder)

        # partially deployed, but this currently means it is deployed
        os.makedirs(os.path.join(install_root, "2019.12.01-py38-rhel7/root"))
        os.makedirs(os.path.join(install_root, "2022.02.02-py38-rhel7/root"))

        _create_links(
            (
                ("2019.12.01-py38-rhel7", "stable"),
                ("2022.02.02-py38-rhel7", "testing"),
            ),
            root=install_root,
        )
        open(os.path.join(release_folder, "2019.12.01.yml"), "a").close()
        open(os.path.join(release_folder, "2022.02.02.yml"), "a").close()

        non_deployed = fetch_non_deployed(install_root, release_folder)
        assert len(non_deployed) == 0, non_deployed
