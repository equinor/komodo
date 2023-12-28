import argparse

from komodo.yaml_file_types import KomodoException, RepositoryFile, UpgradeProposalsFile


def verify_package_versions_exist(
    upgrade_proposals: UpgradeProposalsFile,
    repository: RepositoryFile,
) -> None:
    found_release_with_upgrades = False
    for proposed_package_upgrades in upgrade_proposals.content.values():
        if proposed_package_upgrades is None:
            continue
        found_release_with_upgrades = True
        errors = []
        for (
            upgrade_proposals_package,
            upgrade_proposals_package_version,
        ) in proposed_package_upgrades.items():
            try:
                repository.validate_package_entry(
                    upgrade_proposals_package,
                    upgrade_proposals_package_version,
                )
                print(
                    f"Found package: '{upgrade_proposals_package}' with version"
                    f" {upgrade_proposals_package_version} in repository",
                )
            except KomodoException as e:
                errors.append("ERROR: " + e.error)  # type: ignore
        if errors:
            raise SystemExit("\n".join(errors))
    if found_release_with_upgrades:
        print("No upgrades found")
    else:
        print("Found upgrades")


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate upgrade proposals against the repository file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "upgrade_proposals_file",
        type=UpgradeProposalsFile(),
        help="Upgrade_proposals file to validate",
    )
    parser.add_argument(
        "repofile",
        type=RepositoryFile(),
        help="Repository file to check upgrade_proposals against.",
    )
    return parser.parse_args()


def main() -> None:
    args = get_args()
    verify_package_versions_exist(args.upgrade_proposals_file, args.repofile)
    print("Upgrade proposals file is valid!")


if __name__ == "__main__":
    main()
