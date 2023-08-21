# GitOps Server Helm Chart

# Releasing a new version

1. Modify `pyproject.toml` and set `version = XXX`
2. Modify `gitops/__init__.py` and set `__version__ = "XXX"`
3. Modify `charts/gitops/Chart.yaml` and set `version: "XXX"`
4. Create a github release. Set the release tag to match `XXX`. The github pipeline will do the following: Create a new version of the chart, create a docker image and release a new python library version to pypi.
