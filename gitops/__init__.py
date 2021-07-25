import importlib.metadata

try:
    _DISTRIBUTION_METADATA = importlib.metadata.metadata("gitops")

    __version__ = _DISTRIBUTION_METADATA["Version"]
except importlib.metadata.PackageNotFoundError:
    __version__ = "unknown"
