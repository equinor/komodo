import os


class Data:
    def __init__(self, extra_data_dirs=None) -> None:
        """Create a Data object responsible for giving you the filez you need.
        Takes a list of extra_data_dirs to search.
        """
        self._dirs = [os.path.dirname(__file__)]
        if extra_data_dirs is not None:
            for extra_dir in extra_data_dirs:
                if not os.path.exists(extra_dir):
                    msg = f"Extra data directory {extra_dir} does not exist"
                    raise OSError(
                        msg,
                    )
            self._dirs.extend(extra_data_dirs)

    def get(self, file_name):
        for directory in self._dirs:
            path = os.path.join(directory, file_name)
            if os.path.exists(path):
                return path
        msg = f"no such file {file_name} in {self._dirs}"
        raise OSError(msg)
