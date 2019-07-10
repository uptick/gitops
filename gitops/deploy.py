import logging
from itertools import chain

from .cluster import Cluster
from .git import refresh_repo, temp_repo
from .slack import post

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
    n_success=sum([r['exit_code'] == 0 for r in results.values()])
    n_failed=sum([r['exit_code'] != 0 for r in results.values()])
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
        logger.info(f'Initialising deployer for "{url}".')
        before = push_event['before']
        after = push_event['after']
        self.current_cluster = await self.load_cluster(url, after)
        try:
            self.previous_cluster = await self.load_cluster(url, before)
        except Exception as e:
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
            result = await ns.deploy()
            result['app'] = name
            results[name] = result
            await self.post_deploy_result(result)
        await self.post_final_summary(results)

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
        return url.split('/')[-1].split('.')[0]

    async def post_init_summary(self, changed):
        await post_app_updates(self.current_cluster.name, changed, self.current_cluster.namespaces)

    async def post_deploy_result(self, result):
        await post_app_result(self.current_cluster.name, result)

    async def post_final_summary(self, results):
        await post_app_summary(self.current_cluster.name, results)
