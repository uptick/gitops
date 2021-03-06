import json
import logging
import os
import tempfile

from common.app import App

from . import ACCOUNT_ID, CLUSTER_NAME
from .app_definitions import AppDefinitions
from .git import temp_repo
from .slack import post
from .utils import get_repo_name_from_url, run

BASE_REPO_DIR = '/var/gitops/repos'
ROLE_ARN = f'arn:aws:iam::{ACCOUNT_ID}:role/GitopsAccess'
logger = logging.getLogger('gitops')


async def post_init_summary(source, username, added_apps, updated_apps, removed_apps):
    deltas = ''
    for typ, d in [('Adding', added_apps), ('Updating', updated_apps), ('Removing', removed_apps)]:
        if d:
            deltas += f"\n\t• {typ}: {', '.join(f'`{app}`' for app in sorted(d))}"
    await post(
        f"A deployment from `{source}` has been initiated by *{username}* for cluster `{CLUSTER_NAME}`"
        f", the following apps will be updated:{deltas}"
    )


async def post_result(source, result):
    if result['exit_code'] != 0:
        await post(
            f"Failed to deploy app `{result['app']}` from `{source}` for cluster `{CLUSTER_NAME}`:"
            f"\n>>>{result['output']}"
        )


async def post_result_summary(source, results):
    n_success = sum([r['exit_code'] == 0 for r in results.values()])
    n_failed = sum([r['exit_code'] != 0 for r in results.values()])
    await post(
        f"Deployment from `{source}` for `{CLUSTER_NAME}` results summary:\n"
        f"\t• {n_success} succeeded\n"
        f"\t• {n_failed} failed"
    )


class Deployer:
    async def from_push_event(self, push_event):
        url = push_event['repository']['clone_url']
        self.pusher = push_event['pusher']['name']
        logger.info(f'Initialising deployer for "{url}".')
        before = push_event['before']
        after = push_event['after']
        self.current_app_definitions = await self.load_app_definitions(url, sha=after)
        # TODO: Handle case where there is no previous commit.
        self.previous_app_definitions = await self.load_app_definitions(url, sha=before)

    async def deploy(self):
        added_apps, updated_apps, removed_apps = self.calculate_app_deltas()
        if not (added_apps | updated_apps | removed_apps):
            logger.info('No deltas; aborting.')
            return
        logger.info(f'Running deployment for these deltas: A{list(added_apps)}, U{list(updated_apps)}, R{list(removed_apps)}')
        await post_init_summary(self.current_app_definitions.name, self.pusher, added_apps=added_apps, updated_apps=updated_apps, removed_apps=removed_apps)
        results = {}
        for app_name in (added_apps | updated_apps):
            app = self.current_app_definitions.apps[app_name]
            result = await self.update_app_deployment(app)
            result['app'] = app_name
            results[app_name] = result
            await post_result(self.current_app_definitions.name, result)
        for app_name in removed_apps:
            app = self.previous_app_definitions.apps[app_name]
            result = await self.uninstall_app(app)
            result['app'] = app_name
            results[app_name] = result
            await post_result(self.current_app_definitions.name, result)
        await post_result_summary(self.current_app_definitions.name, results)

    async def uninstall_app(self, app: App):
        logger.info(f'Uninstalling app {app.name!r}.')
        return await run(f"helm uninstall {app.name} -n {app.values['namespace']}", catch=True)

    async def update_app_deployment(self, app: App):
        logger.info(f'Deploying app {app.name!r}.')

        if app.chart.type == "git":
            async with temp_repo(app.chart.git_repo_url, sha=app.chart.git_sha) as chart_folder_path:
                await run(f'cd {chart_folder_path}; helm dependency build')
                with tempfile.NamedTemporaryFile(suffix='.yml') as cfg:
                    cfg.write(json.dumps(app.values).encode())
                    cfg.flush()
                    os.fsync(cfg.fileno())
                    return await run((
                        'helm upgrade'
                        ' --install'
                        f' -f {cfg.name}'
                        f" --namespace={app.values['namespace']}"
                        f' {app.name}'
                        f' {chart_folder_path}'
                    ), catch=True)
        elif app.chart.type == "helm":
            with tempfile.NamedTemporaryFile(suffix='.yml') as cfg:
                cfg.write(json.dumps(app.values).encode())
                cfg.flush()
                os.fsync(cfg.fileno())
                await run(f'helm repo add {app.chart.helm_repo} {app.chart.helm_repo_url}')
                return await run((
                    'helm upgrade'
                    ' --install'
                    f' -f {cfg.name}'
                    f" --namespace={app.values['namespace']}"
                    f' {app.name}'
                    f' {app.chart.helm_chart}'
                ), catch=True)
        else:
            logger.warning("Local is not implemented yet")
            return

    def calculate_app_deltas(self):
        cur = self.current_app_definitions.apps.keys()
        prev = self.previous_app_definitions.apps.keys()

        added = cur - prev
        common = cur & prev
        removed = prev - cur

        updated = set()
        for app_name in common:
            cur_app = self.current_app_definitions.apps[app_name]
            prev_app = self.previous_app_definitions.apps[app_name]
            if cur_app != prev_app:
                if cur_app.is_inactive():
                    logger.info(f'Skipping changes in app {app_name!r}: marked inactive.')
                    continue
                updated.add(app_name)
        return added, updated, removed

    async def load_app_definitions(self, url: str, sha: str):
        logger.info(f'Loading app definitions at "{sha}".')
        async with temp_repo(url, sha=sha) as repo:
            app_definitions = AppDefinitions(get_repo_name_from_url(url))
            app_definitions.from_path(repo)
            return app_definitions
