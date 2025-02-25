import datetime
import re
from pathlib import Path


def diff_month(date_1: datetime.date, date_2: datetime.date) -> int:
    return (date_1.year - date_2.year) * 12 + date_1.month - date_2.month


class Release:
    def __init__(self, release_id: str) -> None:
        self.release_id = release_id

    def __repr__(self) -> str:
        return self.release_id

    def set_python_version(self, python_version: str) -> None:
        self.release_id = self.release_id.split("-")[0] + "-" + python_version

    def month(self) -> str:
        return self.release_id[0:7]

    def month_alias(self) -> str:
        return f"{self.month()}-{self.py_ver()}"

    def monthly_diff(self, other: "Release") -> int:
        """Return monthly difference between this and other."""
        date_a = datetime.datetime.strptime(self.month(), "%Y.%m").date()
        date_b = datetime.datetime.strptime(other.month(), "%Y.%m").date()
        return diff_month(date_a, date_b)

    def is_concrete(self) -> bool:
        """Return whether or not this is a concrete build. 2019.01-py is not a
        concrete build: all komodo builds follow the format 2019.01.???-pyN.
        """
        return len(repr(self)) > len(self.month_alias())

    def py_ver(self) -> str:
        try:
            return re.search(r"-(py\d{1,3})", self.release_id).group(1)
        except TypeError as exc:
            msg = f"{self.release_id} has no python version"
            raise ValueError(msg) from exc
        except AttributeError:
            # In the case that this is a monthly alias without postfix, assume 3.8
            if len(repr(self)) == len("2022.01"):
                return "py38"

            raise

    @staticmethod
    def id_from_file_name(file_name: str):
        return Path(file_name).stem

    @staticmethod
    def path_is_release(path: str) -> bool:
        return Path(path).parent.name == "releases"
