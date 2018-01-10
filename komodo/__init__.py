"""Komodo software distribution build system."""

from .build import make, pypaths
from .fetch import fetch
from .shell import shell, pushd
from .lint import lint
from .maintainer import maintainers

__version__ = '0.0.1'
__author__ = 'Software Innovation Bergen, Statoil ASA'

__copyright__ = 'Copyright 2017, Statoil ASA'
__license__ = 'GNU General Public License, version 3 or any later version'

__credits__ = __author__
__maintainer__ = __author__
__email__ = 'fg_gpl@statoil.com'
__status__ = 'Production'

__ALL__ = ['make', 'fetch', 'shell', 'lint', 'maintainers']
