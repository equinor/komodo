import os
import pytest  # noqa

from komodo import local
from komodo.data import Data


def test_write_local_activators(tmpdir):
    tmpdir = str(tmpdir)  # XXX: python2 support
    locations = {
        "locations": {
            "south1": "computer01.south1.equinor.com",
            "west2": "computer45.west2.equinor.com",
        }
    }
    local_activator_path = os.path.join(tmpdir, "local")
    local_csh_activator_path = os.path.join(tmpdir, "local.csh")
    with open(local_activator_path, "w") as local_activator, open(
        local_csh_activator_path, "w"
    ) as local_activator_csh:
        local.write_local_activators(
            Data(), locations, local_activator, local_activator_csh
        )

    with open(local_activator_path) as activator:
        assert (
            activator.read()
            == """host=$(hostname)
location=$(echo $host | cut -d "-" -f 1)

case ${location} in
   south1)
      export ERT_LSF_SERVER=computer01.south1.equinor.com
        ;;
   west2)
      export ERT_LSF_SERVER=computer45.west2.equinor.com
        ;;
esac
"""
        )

    with open(local_csh_activator_path) as activator:
        assert (
            activator.read()
            == """set host=`hostname`
set location=`echo ${host} | cut -d "-" -f 1`

switch (${location})
   case south1:
        setenv ERT_LSF_SERVER computer01.south1.equinor.com
        breaksw
   case west2:
        setenv ERT_LSF_SERVER computer45.west2.equinor.com
        breaksw
endsw
"""
        )
