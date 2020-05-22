import json
import logging
import os
import tempfile

from . import ACCOUNT_ID, CLUSTER_NAME
from .app_definitions import AppDefinitions
from .git import temp_repo
from .slack import post
from .utils import get_repo_name_from_url, run

BASE_REPO_DIR = '/var/gitops/repos'
ROLE_ARN = f'arn:aws:iam::{ACCOUNT_ID}:role/GitopsAccess'
logger = logging.getLogger('gitops')


async def post_app_updates(source, apps, username=None):
    user_string = f' by *{username}*' if username else ''
    app_list = '\n'.join(f'\t• `{a}`' for a in apps)
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
        # TODO move to function
        await run(f'aws eks update-kubeconfig --kubeconfig /root/.kube/config --region ap-southeast-2 --name {CLUSTER_NAME} --role-arn {ROLE_ARN} --alias {CLUSTER_NAME}')
        results = {}
        for app_name in changed_apps:
            app = self.current_app_definitions.apps[app_name]
            result = await self.deploy_app(app)
            result['app'] = app_name
            results[app_name] = result
            await self.post_deploy_result(result)
        await self.post_final_summary(results)

    async def deploy_app(self, app):
        logger.info(f'Deploying app {app.name!r}.')
        repo, sha = app.values['chart'], None
        if '@' in repo:
            repo, sha = repo.split('@')
        async with temp_repo(repo, 'chart', sha=sha) as repo:
            await run(f'cd {repo}; helm dependency build')
            with tempfile.NamedTemporaryFile(suffix='.yml') as cfg:
                cfg.write(json.dumps(app.values).encode())
                cfg.flush()
                os.fsync(cfg.fileno())
                retry = 0
                while retry < 2:  # TODO: Better retry system
                    results = await run((
                        'helm upgrade'
                        ' --install'
                        f' -f {cfg.name}'
                        f" --namespace={app.values['namespace']}"
                        f' {app.name}'
                        f' {repo}'
                    ), catch=True)
                    # TODO: explain
                    if 'has no deployed releases' in results['output']:
                        logger.info('Purging release.')
                        await run(f'helm delete --purge {app.name}')
                        retry += 1
                    else:
                        break
                return results

    def calculate_changed_apps(self):
        # TODO: If an app has been removed from the list of app definitions, we want to delete its deployment.
        changed = set()
        for name, app in self.current_app_definitions.apps.items():
            prev_app = self.previous_app_definitions.apps.get(name) if self.previous_app_definitions else None
            if app != prev_app:  # prev_app may be None, sfine.
                # If the app has been marked inactive, skip.
                if app.is_inactive():
                    logger.info(f'Skipping changes in app {name!r}: marked inactive.')
                    continue
                # If the app isn't targeting our cluster, skip.
                if app.values['cluster'] != CLUSTER_NAME:
                    logger.info(f"Skipping changes in app {name!r}: targeting different cluster: {app.values['cluster']!r} != {CLUSTER_NAME!r}")
                    continue
                changed.add(name)
        return changed

    async def load_app_definitions(self, url, sha):
        logger.info(f'Loading app definitions at "{sha}".')
        async with temp_repo(url, 'app_definitions', sha=sha) as repo:
            app_definitions = AppDefinitions(get_repo_name_from_url(url))
            app_definitions.from_path(repo)
            return app_definitions

    async def post_init_summary(self, changed_apps):
        await post_app_updates(self.current_app_definitions.name, changed_apps, self.pusher)

    async def post_deploy_result(self, result):
        await post_app_result(self.current_app_definitions.name, result)

    async def post_final_summary(self, results):
        await post_app_summary(self.current_app_definitions.name, results)
