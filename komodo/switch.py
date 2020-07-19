import os
from jinja2 import Template


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
        print("{} existed, doing nothing".format(release_path))
        return

    os.makedirs(release_path)

    with open(os.path.join(release_path, "enable"), "w") as activator, open(
        data.get("activator_switch.tmpl")
    ) as activator_tmpl:
        activator.write(
            Template(activator_tmpl.read(), keep_trailing_newline=True).render(prefix=prefix, release=release_py)
        )

    with open(os.path.join(release_path, "enable.csh"), "w") as activator, open(
        data.get("activator_switch.csh.tmpl")
    ) as activator_tmpl:
        activator.write(
            Template(activator_tmpl.read(), keep_trailing_newline=True).render(prefix=prefix, release=release_py)
        )
