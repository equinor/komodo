from argparse import ArgumentParser
import yaml as yml
import fnmatch
import sys
import os
import shutil
import hashlib


def get_messages_and_scripts(release_name, motd_db):
    scripts = []
    messages = []
    inline = []
    for key in motd_db:
        if fnmatch.fnmatch(release_name, key):
            scripts.extend(motd_db[key].get("scripts", []))
            messages.extend(motd_db[key].get("messages", []))
            inline.extend(motd_db[key].get("inline", []))

    return scripts, messages, inline


def create_inline_messages(messages, dst_path):
    if not os.path.isdir(dst_path):
        os.makedirs(dst_path)
    for msg in messages:
        filename = hashlib.md5(msg.encode()).hexdigest()
        filename = "0Z" + filename  # for orderings sake
        with open(os.path.join(dst_path, filename), "w") as new_file:
            new_file.write(msg)


def copy_files(file_list, dst_path, src_path):
    if not os.path.isdir(dst_path):
        os.makedirs(dst_path)
    for file_name in file_list:
        print("Installing message: {}".format(file_name))
        file_path = os.path.join(src_path, file_name)
        if not os.path.exists(file_path):
            raise SystemExit("ERROR: Message file {} does not exisit".format(file_name))
        shutil.copy(file_path, os.path.join(dst_path, file_name))


def get_parser():
    parser = ArgumentParser(description="Post messages to a release.")

    parser.add_argument(
        "--releases",
        "-r",
        nargs="+",
        help="The releases to post messages to.",
    )

    parser.add_argument(
        "--motd-db",
        "-m",
        required=True,
        help="YML file defining the messages.",
    )

    parser.add_argument(
        "--komodo-prefix",
        "-k",
        required=True,
        help="Path to folder holding komodo-releases.",
    )

    return parser


def main(args=None):
    parser = get_parser()
    args = parser.parse_args(args=args)

    if not os.path.isfile(args.motd_db):
        raise SystemExit(
            "ERROR: The message-database {} was not found".format(args.motd_db)
        )
    with open(args.motd_db) as motd_db_file:
        motd_db = yml.safe_load(motd_db_file)
    motd_path = os.path.dirname(args.motd_db)

    if not os.path.isdir(args.komodo_prefix):
        raise SystemExit("ERROR: Komodo-prefix {} not found".format(args.komodo_prefix))

    # Create list of releases to post to
    releases = args.releases
    if not args.releases:
        releases = os.listdir(args.komodo_prefix)
        try:
            releases.remove(
                "repository"
            )  # repository is not a release in komodo folder
        except ValueError:
            pass

    # Scrap all old messages
    for release_name in releases:
        komodo_path = os.path.join(args.komodo_prefix, release_name)

        if not os.path.isdir(komodo_path):
            raise SystemExit("ERROR: Release {} not found".format(release_name))

        dst_motd_path = os.path.join(komodo_path, "motd")
        if os.path.isdir(dst_motd_path):
            shutil.rmtree(dst_motd_path)

        os.makedirs(dst_motd_path)

    # Post new messages
    for release_name in releases:
        scripts, messages, inline = get_messages_and_scripts(release_name, motd_db)
        if not scripts and not messages and not inline:
            print("WARNING: No messages found for release: {}".format(release_name))
            return

        komodo_path = os.path.join(args.komodo_prefix, release_name)
        dst_motd_path = os.path.join(komodo_path, "motd")

        if scripts:
            copy_files(
                file_list=scripts,
                dst_path=os.path.join(dst_motd_path, "scripts"),
                src_path=os.path.join(motd_path, "scripts"),
            )

        if messages:
            copy_files(
                file_list=messages,
                dst_path=os.path.join(dst_motd_path, "messages"),
                src_path=os.path.join(motd_path, "messages"),
            )

        if inline:
            create_inline_messages(
                messages=inline,
                dst_path=os.path.join(dst_motd_path, "messages"),
            )


if __name__ == "__main__":
    main()
