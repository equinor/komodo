import importlib_metadata

try:
    VERSION = importlib_metadata.distribution(__name__).version
except importlib_metadata.PackageNotFoundError:
    try:
        from ._version import version as VERSION
    except ImportError:
        raise ImportError("Failed to find autogenerated _version.py.") from None
__version__ = VERSION
