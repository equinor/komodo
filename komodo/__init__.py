"""Komodo software distribution build system."""

from .build import make, pypaths
from .fetch import fetch
from .shell import shell, pushd
from .lint import lint
from .cleanup import cleanup
from .maintainer import maintainers

__version__ = '1.0'
__author__ = 'Software Innovation Bergen, Statoil ASA'

__copyright__ = 'Copyright 2017, Statoil ASA'
__license__ = 'GNU General Public License, version 3 or any later version'

__credits__ = __author__
__maintainer__ = __author__
__email__ = 'fg_gpl@statoil.com'
__status__ = 'Production'

__ALL__ = ['make', 'fetch', 'shell', 'lint', 'maintainers']
