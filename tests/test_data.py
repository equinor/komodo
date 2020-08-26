import pytest
from komodo.data import Data


def test_non_existing_extra_data_dir():
    with pytest.raises(IOError):
        Data(["/path/to/nowhere"])
