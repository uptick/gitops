import logging
from itertools import chain

from .cluster import Cluster
from .git import refresh_repo, temp_repo
from .slack import post

BASE_REPO_DIR = '/var/gitops/repos'

logger = logging.getLogger('gitops')


def iter_commits(data):
    for commit in data['commits']:
        yield commit


def iter_changed_files(data):
    for commit in iter_commits(data):
        all_files = chain(
            commit['added'],
            commit['modified'],
            commit['removed']
        )
        for filename in all_files:
            yield filename


def collect_modifications(data):
    seen = set()
    resources = []
    for filename in iter_changed_files(data):
        try:
            resource = Resource.from_changed_file(filename)
            if resource.id not in seen:
                seen.add(resource.id)
                resources.append(resource)
        except ValueError:
            pass
    return resources


async def post_app_updates(cluster, apps, username=None):
    await post((
        'A deployment on the `{}` cluster has been initiated{}'
        ', the following apps will be updated:\n{}'
    ).format(
        cluster,
        f' by {username}' if username else '',
        '\n'.join(f'\t• `{a}`' for a in apps)
    ))


async def post_app_result(cluster, result):
    if result['exit_code'] != 0:
        await post((
            'Failed to deploy app `{}` to cluster `{}`:\n>>>{}'
        ).format(
            result['app'],
            cluster,
            result['output']
        ))


async def post_app_summary(cluster, results):
    await post((
        'Deployment to `{}` results summary:\n'
        '\t• {n_success} succeeded\n'
        '\t• {n_failed} failed'
    ).format(
        cluster,
        n_success=sum([r['exit_code'] == 0 for r in results.values()]),
        n_failed=sum([r['exit_code'] != 0 for r in results.values()])
    ))


async def deploy(data):
    cluster = data['project']['name']
    refresh_repo(
        cluster,
        data['project']['http_url'],
        data['checkout_sha']
    )
    resources = collect_modifications(cluster)
    post_updates(cluster, resources, data['user_username'])
    results = []
    for resource in resources:
        result = resource.deploy()
        post_result(cluster, result)
        results.append(result)
    post_summary(cluster, results)


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
        await post_app_updates(self.current_cluster.name, changed)

    async def post_deploy_result(self, result):
        await post_app_result(self.current_cluster.name, result)

    async def post_final_summary(self, results):
        await post_app_summary(self.current_cluster.name, results)
