import pathlib
import re

pyproject = pathlib.Path("pyproject.toml")
init = pathlib.Path("gitops/__init__.py")
chart = pathlib.Path("charts/gitops/Chart.yaml")
current = re.search(r'version = "(.*)"', pyproject.read_text()).group(1)  # type: ignore

version = input(f"Enter a new version. Currently at ({current}): ").strip()

pyproject_text = pyproject.read_text()
pyproject.write_text(re.sub(r'version = ".*"', f'version = "{version}"', pyproject_text, count=1))

chart_text = chart.read_text()
chart.write_text(re.sub(r"version: .*", f"version: {version}", chart_text, count=1))

init_text = init.read_text()
init.write_text(re.sub(r'__version__ = ".*"', f'__version__ = "{version}"', init_text, count=1))
