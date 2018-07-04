import json
import logging
import os
import tempfile
from base64 import b64encode

from .git import temp_repo
from .utils import load_yaml, run

logger = logging.getLogger('gitops')


class Namespace:
    def __init__(self, name, deployments=None, secrets=None):
        self.name = name
        self.deployments = deployments or {}
        self.secrets = secrets or {}
        self.make_values()

    def __eq__(self, other):
        return (
            self.name == other.name and
            json.dumps(self.values, sort_keys=True) == json.dumps(other.values, sort_keys=True)
        )

    def deploy(self):
        logger.info(f'Deploying namespace "{self.name}".')
        print(json.dumps(self.values, indent=2))
        with temp_repo(self.values['chart'], 'chart') as repo:
            with tempfile.NamedTemporaryFile(suffix='.yml') as cfg:
                cfg.write(json.dumps(self.values).encode())
                cfg.flush()
                os.fsync(cfg.fileno())
                return run((
                    'helm upgrade'
                    ' --install'
                    ' -f {values_file}'
                    ' --namespace={namespace}'
                    ' {name}'
                    ' {path}'
                ).format(
                    name=self.name,
                    namespace=self.values['namespace'],
                    values_file=cfg.name,
                    path=repo
                ))

    def from_path(self, path):
        self.path = path
        self.deployments = load_yaml(os.path.join(path, 'deployment.yml'))
        self.secrets = load_yaml(os.path.join(path, 'secrets.yml')).get('secrets', {})
        self.make_values()

    def make_values(self):
        self.values = {
            **self.deployments,
            'image': self.make_image(self.deployments),
            'secrets': {
                **{
                    k: b64encode(v.encode()).decode()
                    for k, v in self.secrets.items()
                }
            }
        }

    def make_image(self, details):
        if 'image-tag' in details:
            return self.deployments['images']['template'].format(
                tag=details['image-tag']
            )
        elif 'image-group' in details:
            return self.make_image(
                self.deployments['images']['groups'][
                    details['image-group']
                ]
            )
        else:
            return details.get('image')
