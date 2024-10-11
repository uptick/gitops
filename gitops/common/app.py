import json
import os
from base64 import b64encode
from typing import Any

from .utils import load_yaml

DEPLOYMENT_ATTRIBUTES = [
    "tags",
    "image-tag",
    "containers",
    "environment",
    "cluster",
    "bump",
    "namespace",
]


class App:
    def __init__(
        self,
        name: str,
        path: str | None = None,
        deployments: dict | None = None,
        secrets: dict | None = None,
        load_secrets: bool = True,
        encode_secrets: bool = True,
        # deprecated
        account_id: str = "",
    ) -> None:
        """
        :params name: The name of the app
        :params path: The path to the app directory
        :params deployments: The deployments dictionary (injecting for testing)
        :params secrets: The secrets dictionary (injecting for testing)
        :params load_secrets: Whether to load the secrets file
        :params encode_secrets: Whether to base64 encode the secrets
        """
        self.encode_secrets = encode_secrets
        self.name = name
        self.path = path
        self.account_id = account_id
        if path:
            deployments = load_yaml(os.path.join(path, "deployment.yml"))
            if load_secrets:
                secrets = load_yaml(os.path.join(path, "secrets.yml")).get("secrets", {})
        deployments = deployments or {}
        secrets = secrets or {}
        self.values = self._make_values(deployments, secrets)
        self.namespace: str = self.values["namespace"]
        self.chart = Chart(self.values["chart"])

    def __eq__(self, other: object) -> bool:
        return (
            type(self) == type(other)  # noqa
            and isinstance(other, App)
            and self.name == other.name
            and json.dumps(self.values, sort_keys=True) == json.dumps(other.values, sort_keys=True)
        )

    def __repr__(self) -> str:
        return f"App(name={self.name}, cluster={self.cluster}, tags={self.tags})"

    def is_inactive(self) -> bool:
        return "inactive" in self.values.get("tags", [])

    def set_value(self, path: str, value: Any) -> None:
        """Sets the value on the path of self.values
        Usage:
            app.set_value("deployments.label.GITHUB_DEPLOYMENT_KEY", "1")
        """
        keys = path.split(".")
        current_dict = self.values
        for key in keys[:-1]:
            current_dict = current_dict.setdefault(key, {})
        current_dict[keys[-1]] = value

    def _make_values(self, deployments: dict, secrets: dict[str, str]) -> dict:
        def encode(value: str) -> str:
            return b64encode(str(value).encode()).decode() if self.encode_secrets else value

        values = {**deployments, "secrets": {**{k: encode(v) for k, v in secrets.items()}}}

        image = self._make_image(deployments)
        if image:
            values["image"] = image

        # Don't include the `images` key. It will only cause everything to be
        # redeployed when any group changes.
        values.pop("images", None)
        return values

    def _make_image(self, deployment_config: dict) -> str:
        if "image-tag" in deployment_config:
            return deployment_config["images"]["template"].format(
                account_id=self.account_id,
                tag=deployment_config["image-tag"],
            )
        else:
            return deployment_config.get("image", "")

    @property
    def image(self) -> str:
        """[305686791668.dkr.ecr.ap-southeast-2.amazonaws.com/uptick:yoink-9f03ac80f3]"""
        image = self.values.get("image", "")
        if isinstance(image, dict):
            return f"{image['repository']}:{image.get('tag','latest')}"
        else:
            return image

    @property
    def image_repository_name(self) -> str:
        """305686791668.dkr.ecr.ap-southeast-2.amazonaws.com/[uptick]:yoink-9f03ac80f3"""
        return self.image.split(":")[0].split("/")[-1]

    @property
    def image_repository(self) -> str:
        """[305686791668.dkr.ecr.ap-southeast-2.amazonaws.com]/uptick:yoink-9f03ac80f3"""
        return self.image.split("/")[0]


    @property
    def image_tag(self) -> str:
        """305686791668.dkr.ecr.ap-southeast-2.amazonaws.com/uptick:[yoink-9f03ac80f3]"""
        return self.image.split(":")[-1]

    @property
    def image_prefix(self) -> str:
        """Gets the image prefix portion of {prefix}-{git hash}
        305686791668.dkr.ecr.ap-southeast-2.amazonaws.com/uptick:[yoink]-9f03ac80f3

        eg: qa-server-12345 -> qa-server
        """
        if "-" not in self.image_tag:
            return ""
        return self.image_tag.rsplit("-", 1)[0]

    @property
    def cluster(self) -> str:
        return self.values.get("cluster", "")

    @property
    def tags(self) -> list[str]:
        return self.values.get("tags", [])

    @property
    def service_account_name(self) -> str:
        return self.values.get("serviceAccount", {}).get("name") or self.values.get("serviceAccountName") or "default"

    @property
    def secrets(self) -> dict[str, str]:
        # TODO: This should be a first class property
        return self.values.get("secrets", {})


class Chart:
    """Represents a Helm chart

    Can be stored in a git repo, helm repo or local path

    Example definition in `deployments.yml`:
    chart:
      type: git
      git_sha: develop
      git_repo_url: https://github.com/uptick/workforce

    of
    chart:
      type: helm
      helm_repo: brigade
      helm_repo_url: https://brigadecore.github.io/charts
      helm_chart: brigade/brigade

    If a dictionary is not passed, it is assumed to be a git repo. eg:
      chart: https://github.com/uptick/workforce
    """

    def __init__(self, definition: dict | str):
        if isinstance(definition, str):
            # for backwards compat, any chart definition which is a string, is a git repo
            self.type = "git"
            self.git_sha = None
            self.git_repo_url = definition or None
        elif isinstance(definition, dict):
            self.type = definition["type"]
            self.git_sha = definition.get("git_sha")
            self.git_repo_url = definition.get("git_repo_url")
            self.helm_repo = definition.get("helm_repo")
            self.helm_repo_url = definition.get("helm_repo_url")
            self.helm_chart = definition.get("helm_chart")
            self.version = definition.get("version")
            self.path = definition.get("path")
        else:
            raise Exception("Chart definition must be either a dict or string. Instead it is: {definition}")

        if self.git_repo_url and "@" in self.git_repo_url:
            self.git_repo_url, self.git_sha = self.git_repo_url.split("@")
