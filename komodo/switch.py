import os
import shutil

from jinja2 import Template

MIGRATION_WARNING = (
    "Attention! Your machine is running on a RHEL6 environment "
    "which is in the process of being phased out.\n"
    "New versions of komodo will from October 2020 only support RHEL7.\n"
    "Please migrate as soon as possible. If you have any questions or issues - "
    "contact us on #ert-users on Slack or Equinor's Yammer!"
)


def create_activator_switch(data, prefix, release):
    """Given a prefix and a release, create an activator switch which
    will vary the selected activator based on the RHEL version. The data
    argument is expected to be a komodo.data.Data instance."""
    # drop "-rheln"
    try:
        release_py, _ = release.rsplit("-", 1)
    except ValueError:
        # likely a build that does not require an activator switch
        return

    release_path = os.path.join(prefix, release_py)
    if os.path.exists(release_path):
        shutil.rmtree(release_path)

    os.makedirs(release_path)

    with open(os.path.join(release_path, "enable"), "w") as activator, open(
        data.get("activator_switch.tmpl")
    ) as activator_tmpl:
        activator.write(
            Template(activator_tmpl.read(), keep_trailing_newline=True).render(
                prefix=prefix, release=release_py, migration_warning=MIGRATION_WARNING
            )
        )

    with open(os.path.join(release_path, "enable.csh"), "w") as activator, open(
        data.get("activator_switch.csh.tmpl")
    ) as activator_tmpl:
        activator.write(
            Template(activator_tmpl.read(), keep_trailing_newline=True).render(
                prefix=prefix, release=release_py, migration_warning=MIGRATION_WARNING
            )
        )
