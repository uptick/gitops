import pathlib
import re

pyproject = pathlib.Path("pyproject.toml")
init = pathlib.Path("gitops/__init__.py")
chart = pathlib.Path("charts/gitops/Chart.yaml")

version = input("Enter a new version eg: (0.9.1): ").strip()

pyproject_text = pyproject.read_text()
pyproject.write_text(re.sub(r'version = ".*"', f'version = "{version}"', pyproject_text, count=1))

chart_text = chart.read_text()
chart.write_text(re.sub(r"version: .*", f"version: {version}", chart_text, count=1))

init_text = init.read_text()
init.write_text(re.sub(r'__version__ = ".*"', f'__version__ = "{version}"', init_text, count=1))
