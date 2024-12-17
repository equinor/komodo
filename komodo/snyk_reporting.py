import argparse
import html
import os
import sys
from typing import Any

from snyk import SnykClient
from snyk.models import Organization, Vulnerability

from komodo.yaml_file_types import ReleaseDir, ReleaseFile, RepositoryFile

_CONSOLE_VULNERABILITY_FORMAT = """\t{id}
\t\tPackage: {package}
\t\tVersion: {version}
\t\tTitle: {title}
\t\tURL: {url}
\t\tIdentifiers: {identifiers}
\t\tSeverity: {severity}
"""

_GITHUB_VULNERABILITY_FORMAT = (
    "| {id} | {package} | {version} | {title} | {url} | {identifiers} | {severity} |\n"
)


def main() -> None:
    api_token = os.getenv("SNYK_API_TOKEN")
    args = parse_args(sys.argv[1:])
    releases = args.release_folder if args.release_folder else args.release

    vulnerabilities = snyk_main(
        releases=releases,
        repository=args.repo.content,
        api_token=api_token,
        org_id=args.orgid,
    )

    if args.format_github:
        print(_format_github(vulnerabilities=vulnerabilities))
    else:
        print(_format_console(vulnerabilities=vulnerabilities))


def parse_args(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test a release for security and license issues.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--orgid",
        type=str,
        required=True,
        help="The Snyk organization ID.",
    )
    parser.add_argument(
        "--repo",
        type=RepositoryFile(),
        required=True,
        help="A Komodo repository file, in YAML format.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--release",
        type=ReleaseFile(),
        help="A Komodo release file mapping package name to version, in YAML format.",
    )
    group.add_argument(
        "--release-folder",
        type=ReleaseDir(),
        help="A directory containing Komodo release files.",
    )
    parser.add_argument(
        "--format-github",
        action="store_true",
        help=(
            "Flag to print vulnerabilities in GitHub-friendly format vs console format."
        ),
    )

    return parser.parse_args(args)


def filter_pip_packages(
    packages: dict[str, str],
    repository: dict[str, Any],
) -> dict[str, str]:
    return {
        package_name: version
        for (package_name, version) in packages.items()
        if repository[package_name][version].get("make") == "pip"
    }


def create_snyk_search_string(packages: dict[str, str]) -> str:
    return "\n".join(
        [f"{package_name}=={version}" for package_name, version in packages.items()],
    )


def get_unique_issues(issues: list[Vulnerability]) -> list[Vulnerability]:
    ids = set()
    result = []
    for issue in issues:
        if issue.id in ids:
            continue
        result.append(issue)
        ids.add(issue.id)
    return result


def filter_vulnerability_issues(
    snyk_issues: list[Vulnerability], release_packages: dict[str, str]
):
    filtered_vulnerability_issues = []
    for snyk_issue in snyk_issues:
        vulnerable_package_name = snyk_issue.package
        vulnerable_package_version = snyk_issue.version
        if release_packages.get(vulnerable_package_name) == vulnerable_package_version:
            filtered_vulnerability_issues.append(snyk_issue)
    return filtered_vulnerability_issues


def find_vulnerabilities(
    releases: dict[str, dict[str, str]],
    repository: dict[str, Any],
    org: Organization,
) -> dict[str, list[Vulnerability]]:
    result = {}

    for release_name, packages in releases.items():
        pip_packages = filter_pip_packages(packages=packages, repository=repository)
        snyk_search_string = create_snyk_search_string(pip_packages)
        snyk_result = org.test_pipfile(snyk_search_string)
        vulnerability_issues = get_unique_issues(snyk_result.issues.vulnerabilities)
        filtered_vulnerabity_issues = filter_vulnerability_issues(
            vulnerability_issues, packages
        )
        result[release_name] = filtered_vulnerabity_issues
    return result


def _format_console(vulnerabilities: dict[str, list[Vulnerability]]) -> str:
    result = "Security Vulnerabilities:\n"
    for release, vulns in vulnerabilities.items():
        result += release + "\n"
        if not vulns:
            result += "No security vulnerabilities found!\n"
            continue
        for vul in vulns:
            result += _CONSOLE_VULNERABILITY_FORMAT.format(
                id=vul.id,
                package=vul.package,
                version=vul.version,
                title=vul.title,
                url=vul.url,
                identifiers=vul.identifiers,
                severity=vul.severity,
            )
        result += "\n"
    return result


def _format_github(vulnerabilities: dict[str, list[Vulnerability]]) -> str:
    result = "Snyk Security Report\n==\n\n"
    for release, vulns in vulnerabilities.items():
        result += f"{release}\n--\n"
        if not vulns:
            result += "No security vulnerabilities found!\n"
            continue
        result += (
            "| id | Package | Version | Title | URL | Identifiers | Severity |\n"
            "| - | - | - | - | - | - | - |\n"
        )
        for vul in vulns:
            result += _GITHUB_VULNERABILITY_FORMAT.format(
                id=vul.id,
                package=vul.package,
                version=vul.version,
                title=vul.title,
                url=vul.url,
                identifiers=vul.identifiers,
                severity=vul.severity,
            )
        result += "\n"
    return html.escape(result)


def _get_org(api_token: str, org_id: str) -> Organization:
    client = SnykClient(api_token)
    return client.organizations.get(org_id)


def snyk_main(
    releases: dict[str, dict[str, str]],
    repository: dict[str, Any],
    api_token: str | None,
    org_id: str,
) -> dict[str, list[Vulnerability]]:
    if api_token is None:
        msg = "No api token given, please set the environment variable SNYK_API_TOKEN."
        raise ValueError(
            msg,
        )

    org = _get_org(api_token, org_id)

    return find_vulnerabilities(
        releases=releases,
        repository=repository,
        org=org,
    )


if __name__ == "__main__":
    main()
