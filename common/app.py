import json
import os
from base64 import b64encode
from typing import Dict, Optional

from .utils import load_yaml

DEPLOYMENT_ATTRIBUTES = [
    'tags',
    'image-tag',
    'containers',
    'environment',
]


class App:
    def __init__(self,
        name: str,
        path: Optional[str] = None,
        deployments: Optional[Dict] = None,
        secrets: Optional[Dict] = None,
        load_secrets: bool = True,
        account_id: str = ''
    ):
        self.name = name
        self.path = path
        self.account_id = account_id
        self.deployments = deployments or {}
        self.secrets = secrets or {}
        if path:
            self.deployments = load_yaml(os.path.join(path, 'deployment.yml'))
            if load_secrets:
                self.secrets = load_yaml(os.path.join(path, 'secrets.yml')).get('secrets', {})
            else:
                self.secrets = secrets or {}
        self.values = self._make_values()

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and self.name == other.name
            and json.dumps(self.values, sort_keys=True) == json.dumps(other.values, sort_keys=True)
        )

    def is_inactive(self):
        return 'inactive' in self.values.get('tags', [])

    def _make_values(self) -> Dict:
        values = {
            **self.deployments,
            'secrets': {
                **{
                    k: b64encode(v.encode()).decode()
                    for k, v in self.secrets.items()
                }
            }
        }

        image = self._make_image(self.deployments)
        if image:
            values['image'] = image

        # Don't include the `images` key. It will only cause everything to be
        # redeployed when any group changes.
        values.pop('images', None)
        return values

    def _make_image(self, deployment_config: Dict):
        if 'image-tag' in deployment_config:
            return deployment_config['images']['template'].format(
                account_id=self.account_id,
                tag=deployment_config['image-tag'],
            )
        else:
            return deployment_config.get('image')
