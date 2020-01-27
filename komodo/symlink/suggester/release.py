import ntpath
import os
import re
from datetime import datetime


def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def diff_month(d1, d2):
    return (d1.year - d2.year) * 12 + d1.month - d2.month


class Release(object):
    def __init__(self, release_id):
        self.release_id = release_id

    def __repr__(self):
        return self.release_id

    def month(self):
        return self.release_id[0:7]

    def month_alias(self):
        return "{}-{}".format(self.month(), self.py_ver())

    def monthly_diff(self, other):
        """Return monthly difference between this and other."""
        date_a = datetime.strptime(self.month(), "%Y.%m").date()
        date_b = datetime.strptime(other.month(), "%Y.%m").date()
        return diff_month(date_a, date_b)

    def is_concrete(self):
        """Return whether or not this is a concrete build. 2019.01-py is not a
        concrete build: all komodo builds follow the format 2019.01.???-pyN."""
        return len(repr(self)) > len(self.month_alias())

    def py_ver(self):
        try:
            return re.search("-(py\\d\\.?\\d?)", self.release_id).group(1)
        except TypeError:
            raise ValueError("{} has no python version".format(self.release_id))
        except AttributeError as attr_error:
            # in the case that this is a monthly alias without postfix, assume
            # py27
            if len(repr(self)) == 7:
                return "py27"

            raise attr_error

    @staticmethod
    def id_from_file_name(file_name):
        no_ext = os.path.splitext(file_name)[0]
        leaf = path_leaf(no_ext)
        return leaf

    @staticmethod
    def path_is_release(path):
        return ntpath.split(path)[0] == "releases"
