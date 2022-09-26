import os


class Data(object):
    def __init__(self, extra_data_dirs=None):
        """Create a Data object responsible for giving you the filez you need.
        Takes a list of extra_data_dirs to search."""
        self._dirs = [os.path.dirname(__file__)]
        if extra_data_dirs is not None:
            for extra_dir in extra_data_dirs:
                if not os.path.exists(extra_dir):
                    raise IOError(
                        "Extra data directory {} does not exist".format(extra_dir)
                    )
            self._dirs.extend(extra_data_dirs)

    def get(self, file_name):
        for d in self._dirs:
            path = os.path.join(d, file_name)
            if os.path.exists(path):
                return path
        raise IOError("no such file {} in {}".format(file_name, self._dirs))
