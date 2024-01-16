#!/bin/bash

set -xe

while test $# -gt 0; do
    case "$1" in
        --fakeroot)
            shift
            export FAKEROOT=$1
            ;;
       --prefix)
            shift
            export PREFIX=$1
            ;;
        --virtualenv)
            shift
            export VIRTUALENV=$1
            ;;
        --virtualenv-interpreter)
            shift
            export VIRTUALENV_INTERPRETER=$1
            ;;
        *)
            export OPTS="$OPTS $1"
            ;;
    esac
    shift
done
out=${FAKEROOT}${PREFIX}

# Create venv
$python -m venv --symlinks --without-pip $out >&2

# Delete unwanted scripts
rm -f $out/bin/activate*
rm -f $out/bin/Activate.ps1

# Replace binaries with shims
for bin in $out/bin/python*; do
    rm $bin
    cat >$bin <<EOF
#!/bin/sh
test -f /opt/rh/rh-python38/root/usr/bin/python3.8 && exec -a "\$0" /opt/rh/rh-python38/root/usr/bin/python3.8 "\$@"
test -f /usr/bin/python3.8 && exec -a "\$0" /usr/bin/python3.8 "\$@"
test -f "$python" && exec -a "\$0" "$python" "\$@"

echo "FATAL: Python 3.8 not found. Looked in:" >&2
echo "    /opt/rh/rh-python38/root/usr/bin/python3.8" >&2
echo "    /usr/bin/python3.8" >&2
echo "    $python" >&2
exit 1
EOF
    chmod +x $bin
done
