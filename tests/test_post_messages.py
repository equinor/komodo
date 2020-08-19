import yaml
import os
import pytest
import hashlib
from komodo.post_messages import get_messages_and_scripts, copy_files, main
from tests import _get_test_root


def test_get_messages():
    motd_db_file = os.path.join(_get_test_root(), "data/test_messages/motd_db.yml")
    with open(motd_db_file) as f:
        motd_db = yaml.safe_load(f)

    release = "2020.01.01-py27-rhel6"
    scripts, messages, inline = get_messages_and_scripts(release, motd_db)
    assert "script1" in scripts
    assert "message1" not in messages
    assert inline is not []

    release = "2020.01.01-py36-rhel6"
    scripts, messages, inline = get_messages_and_scripts(release, motd_db)
    assert "script1" not in scripts
    assert "message1" in messages
    assert inline is not []


def test_main_success(tmpdir):
    with tmpdir.as_cwd():
        motd_db_file = os.path.join(_get_test_root(), "data/test_messages/motd_db.yml")

        release = "2020.01.01-py36-rhel6"
        os.mkdir(release)
        args = [
            "--release",
            release,
            "--motd-db",
            motd_db_file,
            "--komodo-prefix",
            os.getcwd(),
        ]
        main(args)
        assert "message1" in os.listdir(os.path.join(release, "motd", "messages"))


def test_main_success_no_release(tmpdir):
    with tmpdir.as_cwd():
        motd_db_file = os.path.join(_get_test_root(), "data/test_messages/motd_db.yml")

        os.mkdir("2020.01.01-py36-rhel6")
        os.mkdir("2020.01.01-py27-rhel6")
        args = [
            "--motd-db",
            motd_db_file,
            "--komodo-prefix",
            os.getcwd(),
        ]
        main(args)
        assert "message1" in os.listdir(
            os.path.join("2020.01.01-py36-rhel6", "motd", "messages")
        )
        assert "script1" in os.listdir(
            os.path.join("2020.01.01-py27-rhel6", "motd", "scripts")
        )


def test_main_not_existing_release(tmpdir):
    with tmpdir.as_cwd():
        motd_db_file = os.path.join(_get_test_root(), "data/test_messages/motd_db.yml")

        release = "2020.01.01-py36-rhel6"

        args = [
            "--release",
            release,
            "--motd-db",
            motd_db_file,
            "--komodo-prefix",
            os.getcwd(),
        ]
        with pytest.raises(SystemExit) as excinfo:
            main(args)
            assert "Release {} not found".format(release) in str(excinfo.value)


def test_main_no_db(tmpdir):
    with tmpdir.as_cwd():
        motd_db_file = os.path.join(_get_test_root(), "data/test_messages/motd.yml")

        release = "no-message-db"
        os.mkdir(release)
        args = [
            "--release",
            release,
            "--motd-db",
            motd_db_file,
            "--komodo-prefix",
            os.getcwd(),
        ]
        with pytest.raises(SystemExit) as excinfo:
            main(args)
            assert "The message-database {} was not found".format(motd_db_file) in str(
                excinfo.value
            )


def test_main_missing_message_file(tmpdir):
    with tmpdir.as_cwd():
        motd_db_file = os.path.join(_get_test_root(), "data/test_messages/motd.yml")

        release = "no-message"
        os.mkdir(release)
        args = [
            "--release",
            release,
            "--motd-db",
            motd_db_file,
            "--komodo-prefix",
            os.getcwd(),
        ]
        with pytest.raises(SystemExit) as excinfo:
            main(args)
            assert "message file {} does not exisit".format("not-existing") in str(
                excinfo.value
            )


def test_main_success_symlinks(tmpdir):
    with tmpdir.as_cwd():
        motd_db_file = os.path.join(_get_test_root(), "data/test_messages/motd_db.yml")

        os.mkdir("2020.01.01-py36-rhel6")
        os.mkdir("2020.01.01-py27-rhel6")
        os.symlink("2020.01.01-py27-rhel6", "stable")
        args = [
            "--motd-db",
            motd_db_file,
            "--komodo-prefix",
            os.getcwd(),
        ]
        main(args)
        assert "message1" in os.listdir(
            os.path.join("2020.01.01-py36-rhel6", "motd", "messages")
        )
        assert "script1" in os.listdir(
            os.path.join("2020.01.01-py27-rhel6", "motd", "scripts")
        )
        with open(motd_db_file) as f:
            motd_db = yaml.safe_load(f)
        msg = motd_db["stable"]["inline"][0]
        filename = hashlib.md5(msg.encode()).hexdigest()
        filename = "0Z" + filename  # for orderings sake
        assert filename in os.listdir(
            os.path.join("2020.01.01-py27-rhel6", "motd", "messages")
        )
