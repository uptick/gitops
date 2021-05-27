import importlib.metadata

_DISTRIBUTION_METADATA = importlib.metadata.metadata('gitops')

__version__ = _DISTRIBUTION_METADATA['Version']
