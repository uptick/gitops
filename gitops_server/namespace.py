import json
import logging
import os
import tempfile
from base64 import b64encode

from .git import temp_repo
from .utils import load_yaml, run

logger = logging.getLogger('gitops')


class Namespace:
    def __init__(self, name, path=None, deployments={}, secrets={}):
        self.name = name
        self.path = path
        if path:
            self.deployments = load_yaml(os.path.join(path, 'deployment.yml'))
            self.secrets = load_yaml(os.path.join(path, 'secrets.yml')).get('secrets', {})
        else:
            self.deployments = deployments
            self.secrets = secrets
        self.make_values()

    def __eq__(self, other):
        return (
            self.name == other.name
            and json.dumps(self.values, sort_keys=True) == json.dumps(other.values, sort_keys=True)
        )

    def is_inactive(self):
        return 'inactive' in self.values.get('tags', [])

    async def deploy(self):
        logger.info(f'Deploying namespace "{self.name}".')
        async with temp_repo(self.values['chart'], 'chart') as repo:
            await run('helm init --client-only')
            await run(f'cd {repo}; helm dependency build')
            with tempfile.NamedTemporaryFile(suffix='.yml') as cfg:
                cfg.write(json.dumps(self.values).encode())
                cfg.flush()
                os.fsync(cfg.fileno())
                retry = 0
                while retry < 2:  # TODO: Better retry system
                    results = await run((
                        'helm upgrade'
                        ' --install'
                        ' --timeout 600'
                        f' -f {cfg.name}'
                        f' --namespace={self.values["namespace"]}'
                        f' {self.name}'
                        f' {repo}'
                    ), catch=True)
                    # TODO: explain
                    if 'has no deployed releases' in results['output']:
                        logger.info(f'Purging release.')
                        await run((
                            'helm delete'
                            ' --purge'
                            f' {self.name}'
                        ))
                        retry += 1
                    else:
                        break
                return results

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
        # Don't include the `images` key. It will only cause everything to be
        # redeployed when any group changes.
        try:
            del self.values['images']
        except KeyError:
            pass

    def make_image(self, details):
        if 'image-tag' in details:
            return self.deployments['images']['template'].format(
                tag=details['image-tag']
            )
        else:
            return details.get('image')
