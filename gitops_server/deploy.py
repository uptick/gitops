import json
import logging
import os
import tempfile

from . import CLUSTER_NAME
from .app_definitions import AppDefinitions
from .git import temp_repo
from .slack import post
from .utils import get_repo_name_from_url, run

BASE_REPO_DIR = '/var/gitops/repos'

logger = logging.getLogger('gitops')


async def post_app_updates(source, apps, namespaces, username=None):
    user_string = f' by {username}' if username else ''
    app_list = '\n'.join(f'\t• `{a}`' for a in apps if not namespaces[a].is_inactive())
    await post(
        f'A deployment from `{source}` has been initiated{user_string} for cluster `{CLUSTER_NAME}`'
        f', the following apps will be updated:\n{app_list}'
    )


async def post_app_result(source, result):
    if result['exit_code'] != 0:
        await post(
            f'Failed to deploy app `{result["app"]}` from `{source}` for cluster `{CLUSTER_NAME}`:'
            f'\n>>>{result["output"]}'
        )


async def post_app_summary(source, results):
    n_success = sum([r['exit_code'] == 0 for r in results.values()])
    n_failed = sum([r['exit_code'] != 0 for r in results.values()])
    await post(
        f'Deployment from `{source}` for `{CLUSTER_NAME}` results summary:\n'
        f'\t• {n_success} succeeded\n'
        f'\t• {n_failed} failed'
    )


class Deployer:
    async def from_push_event(self, push_event):
        url = push_event['repository']['clone_url']
        self.pusher = push_event['pusher']['name']
        logger.info(f'Initialising deployer for "{url}".')
        before = push_event['before']
        after = push_event['after']
        self.current_app_definitions = await self.load_app_definitions(url, after)
        try:
            self.previous_app_definitions = await self.load_app_definitions(url, before)
        except Exception:
            logger.warning('An exception was generated loading previous app definitions state.')
            self.previous_app_definitions = None

    async def deploy(self):
        changed_apps = self.calculate_changed_apps()
        logger.info(f'Running deployment for these changed apps: {changed_apps}')
        if not len(changed_apps):
            logger.info('Nothing to deploy, aborting.')
            return
        await self.post_init_summary(changed_apps)
        results = {}
        for app_name in changed_apps:
            ns = self.current_app_definitions.namespaces[app_name]
            # If the namespace has been marked inactive, skip.
            if ns.is_inactive():
                logger.info('Skipping deploy; app marked inactive.')
                continue
            # If the namespace isn't targeting our cluster, skip.
            if ns.get_target_cluster() != CLUSTER_NAME:
                logger.info(f'Skipping deploy; app targeting different cluster: {ns.get_target_cluster()!r} != {CLUSTER_NAME!r}')
                continue
            result = await self.deploy_namespace(ns)
            result['app'] = app_name
            results[app_name] = result
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
                        logger.info('Purging release.')
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

    def calculate_changed_apps(self):
        changed = set()
        for name, namespace in self.current_app_definitions.namespaces.items():
            old_namespace = self.previous_app_definitions.namespaces.get(name) if self.previous_app_definitions else None
            if old_namespace:
                if namespace != old_namespace:
                    changed.add(name)
            else:
                changed.add(name)
        return changed

    async def load_app_definitions(self, url, sha):
        logger.info(f'Loading app definitions at "{sha}".')
        async with temp_repo(url, 'app_definitions', sha=sha) as repo:
            app_definitions = AppDefinitions(get_repo_name_from_url(url))
            app_definitions.from_path(repo)
            return app_definitions

    async def post_init_summary(self, changed):
        await post_app_updates(self.current_app_definitions.name, changed, self.current_app_definitions.namespaces, self.pusher)

    async def post_deploy_result(self, result):
        await post_app_result(self.current_app_definitions.name, result)

    async def post_final_summary(self, results):
        await post_app_summary(self.current_app_definitions.name, results)
