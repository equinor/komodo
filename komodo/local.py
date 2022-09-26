import operator

from jinja2 import Template


def write_local_activators(data, defs, local, local_csh):
    with open(data.get("local.tmpl")) as local_tmpl, open(
        data.get("local.csh.tmpl")
    ) as local_csh_tmpl:
        locs = [
            {"loc": loc, "srv": srv}
            for loc, srv in sorted(
                defs["locations"].items(), key=operator.itemgetter(0)
            )
        ]
        local.write(
            Template(local_tmpl.read(), keep_trailing_newline=True).render(locs=locs)
        )
        local_csh.write(
            Template(local_csh_tmpl.read(), keep_trailing_newline=True).render(
                locs=locs
            )
        )
