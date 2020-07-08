import os
from textwrap import dedent


shim_template = dedent("""\
    #!/bin/bash
    root=$(dirname $0)/..
    prog=$(basename $0)
    export LD_LIBRARY_PATH=$root/lib:$root/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
    $root/libexec/$prog "$@"
""")


def create_shims(root):
    print("Creating libexec/ and shims in bin/")

    bin_path = os.path.join(root, "bin")
    libexec_path = os.path.join(root, "libexec")
    os.rename(bin_path, libexec_path)
    os.mkdir(bin_path)
    for name in os.listdir(libexec_path):
        src = os.path.join(libexec_path, name)
        dst = os.path.join(bin_path, name)

        print("{} -> {}".format(src, dst))

        if os.path.isdir(src):
            continue
        with open(dst, "w") as f:
            f.write(shim_template)
        os.chmod(dst, 0o755)
