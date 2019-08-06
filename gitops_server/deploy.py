import json
import logging
import os
import tempfile

from .cluster import Cluster
from .git import temp_repo
from .slack import post
from .utils import run

BASE_REPO_DIR = '/var/gitops/repos'

logger = logging.getLogger('gitops')


async def post_app_updates(cluster, apps, namespaces, username=None):
    user_string = f' by {username}' if username else ''
    app_list = '\n'.join(f'\t• `{a}`' for a in apps if not namespaces[a].is_inactive())
    await post(
        f'A deployment on the `{cluster}` cluster has been initiated{user_string}'
        f', the following apps will be updated:\n{app_list}'
    )


async def post_app_result(cluster, result):
    if result['exit_code'] != 0:
        await post(
            f'Failed to deploy app `{result["app"]}` to cluster `{cluster}`:\n>>>{result["output"]}'
        )


async def post_app_summary(cluster, results):
    n_success = sum([r['exit_code'] == 0 for r in results.values()])
    n_failed = sum([r['exit_code'] != 0 for r in results.values()])
    await post(
        f'Deployment to `{cluster}` results summary:\n'
        f'\t• {n_success} succeeded\n'
        f'\t• {n_failed} failed'
    )


class Deployer:
    def __init__(self):
        pass

    async def from_push_event(self, push_event):
        url = push_event['repository']['clone_url']
        self.pusher = push_event['pusher']['name']
        logger.info(f'Initialising deployer for "{url}".')
        before = push_event['before']
        after = push_event['after']
        self.current_cluster = await self.load_cluster(url, after)
        try:
            self.previous_cluster = await self.load_cluster(url, before)
        except Exception:
            logger.warning('An exception was generated loading previous cluster state.')
            self.previous_cluster = None

    async def deploy(self):
        changed = self.calculate_changed()
        logger.info(f'Running deployment with these changes: {changed}')
        if not len(changed):
            logger.info('Nothing to deploy, aborting.')
            return
        await self.post_init_summary(changed)
        results = {}
        for name in changed:
            ns = self.current_cluster.namespaces[name]
            # If the namespace has been marked inactive, skip.
            if ns.is_inactive():
                continue
            result = await self.deploy_namespace(ns)
            result['app'] = name
            results[name] = result
            await self.post_deploy_result(result)
        await self.post_final_summary(results)

    async def deploy_namespace(self, namespace):
        logger.info(f'Deploying namespace "{namespace.name}".')
        async with temp_repo(namespace.values['chart'], 'chart') as repo:
            await run('helm init --client-only')
            await run((
                'cd {}; '
                'helm dependency build'
            ).format(
                repo
            ))
            with tempfile.NamedTemporaryFile(suffix='.yml') as cfg:
                cfg.write(json.dumps(namespace.values).encode())
                cfg.flush()
                os.fsync(cfg.fileno())
                retry = 0
                while retry < 2:  # TODO: Better retry system
                    results = await run((
                        'helm upgrade'
                        ' --install'
                        ' --timeout 600'
                        ' -f {values_file}'
                        ' --namespace={namespace}'
                        ' {name}'
                        ' {path}'
                    ).format(
                        name=namespace.name,
                        namespace=namespace.values['namespace'],
                        values_file=cfg.name,
                        path=repo
                    ), catch=True)
                    # TODO: explain
                    if 'has no deployed releases' in results['output']:
                        logger.info(f'Purging release.')
                        await run((
                            'helm delete'
                            ' --purge'
                            ' {name}'
                        ).format(
                            name=namespace.name,
                        ))
                        retry += 1
                    else:
                        break
                return results

    def calculate_changed(self):
        changed = set()
        for name, namespace in self.current_cluster.namespaces.items():
            old_namespace = self.previous_cluster.namespaces.get(name) if self.previous_cluster else None
            if old_namespace:
                if namespace != old_namespace:
                    changed.add(name)
            else:
                changed.add(name)
        return changed

    async def load_cluster(self, url, sha):
        logger.info(f'Loading cluster at "{sha}".')
        async with temp_repo(url, 'cluster', sha=sha) as repo:
            cluster = Cluster(self.get_name_from_url(url))
            cluster.from_path(repo)
            return cluster

    def get_name_from_url(self, url):
        # https://github.com/user/repo-name.git > repo-name
        return url.split('/')[-1].split('.')[0]

    async def post_init_summary(self, changed):
        await post_app_updates(self.current_cluster.name, changed, self.current_cluster.namespaces, self.pusher)

    async def post_deploy_result(self, result):
        await post_app_result(self.current_cluster.name, result)

    async def post_final_summary(self, results):
        await post_app_summary(self.current_cluster.name, results)
