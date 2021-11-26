import asyncio
import json
import logging
import os
import tempfile
import uuid
from typing import List, Optional

from gitops.common.app import App
from gitops_server import settings
from gitops_server.types import AppDefinitions, UpdateAppResult
from gitops_server.utils import get_repo_name_from_url, github, run, slack
from gitops_server.utils.git import temp_repo

BASE_REPO_DIR = "/var/gitops/repos"
ROLE_ARN = f"arn:aws:iam::{settings.ACCOUNT_ID}:role/GitopsAccess"
logger = logging.getLogger("gitops")
GITOPS_MAX_PARALLEL_DEPLOYS = os.environ.get("GITOPS_MAX_PARALLEL_DEPLOYS", "5")


async def post_init_summary(
    source, username, added_apps, updated_apps, removed_apps, commit_message
):
    deltas = ""
    for typ, d in [("Adding", added_apps), ("Updating", updated_apps), ("Removing", removed_apps)]:
        if d:
            deltas += f"\n\t• {typ}: {', '.join(f'`{app}`' for app in sorted(d))}"
    await slack.post(
        f"A deployment from `{source}` has been initiated by *{username}* for cluster"
        f" `{settings.CLUSTER_NAME}`, the following apps will be updated:{deltas}\nCommit Message:"
        f" {commit_message}"
    )


async def post_result(app: App, source: str, result: UpdateAppResult):
    github_deployment_url = str(app.values.get("github/deployment_url", ""))
    if result["exit_code"] != 0:
        await github.update_deployment(
            github_deployment_url,
            status=github.STATUSES.failure,
            description=f"Failed to deploy app. {result['output']}",
        )
        await slack.post(
            f"Failed to deploy app `{result['app_name']}` from `{source}` for cluster"
            f" `{settings.CLUSTER_NAME}`:\n>>>{result['output']}"
        )
    else:
        await github.update_deployment(
            github_deployment_url,
            status=github.STATUSES.in_progress,
            description="Helm installed app into cluster. Waiting for pods to deploy.",
        )


async def post_result_summary(source: str, results: List[UpdateAppResult]):
    n_success = sum([r["exit_code"] == 0 for r in results])
    n_failed = sum([r["exit_code"] != 0 for r in results])
    await slack.post(
        f"Deployment from `{source}` for `{settings.CLUSTER_NAME}` results summary:\n"
        f"\t• {n_success} succeeded\n"
        f"\t• {n_failed} failed"
    )


async def load_app_definitions(url: str, sha: str) -> AppDefinitions:
    logger.info(f'Loading app definitions at "{sha}".')
    async with temp_repo(url, sha=sha) as repo:
        app_definitions = AppDefinitions(name=get_repo_name_from_url(url))
        app_definitions.from_path(repo)
        return app_definitions


class Deployer:
    def __init__(
        self,
        pusher: str,
        commit_message: str,
        current_app_definitions: AppDefinitions,
        previous_app_definitions: AppDefinitions,
        skip_migrations: bool = False,
    ):
        self.pusher = pusher
        self.commit_message = commit_message
        self.current_app_definitions = current_app_definitions
        self.previous_app_definitions = previous_app_definitions
        self.deploy_id = str(uuid.uuid4())
        self.skip_migrations = skip_migrations
        # Max parallel helm installs at a time
        # Kube api may rate limit otherwise
        self.semaphore = asyncio.Semaphore(int(GITOPS_MAX_PARALLEL_DEPLOYS))

    @classmethod
    async def from_push_event(cls, push_event):
        url = push_event["repository"]["clone_url"]
        pusher = push_event["pusher"]["name"]
        commit_message = push_event.get("head_commit", {}).get("message")
        skip_migrations = "--skip-migrations" in commit_message
        logger.info(f'Initialising deployer for "{url}".')
        before = push_event["before"]
        after = push_event["after"]
        current_app_definitions = await load_app_definitions(url, sha=after)
        # TODO: Handle case where there is no previous commit.
        previous_app_definitions = await load_app_definitions(url, sha=before)
        return cls(
            pusher,
            commit_message,
            current_app_definitions,
            previous_app_definitions,
            skip_migrations,
        )

    async def deploy(self):
        added_apps, updated_apps, removed_apps = self.calculate_app_deltas()
        if not (added_apps | updated_apps | removed_apps):
            logger.info("No deltas; aborting.")
            return
        logger.info(
            f"Running deployment for these deltas: A{list(added_apps)}, U{list(updated_apps)},"
            f" R{list(removed_apps)}"
        )
        await post_init_summary(
            self.current_app_definitions.name,
            self.pusher,
            added_apps=added_apps,
            updated_apps=updated_apps,
            removed_apps=removed_apps,
            commit_message=self.commit_message,
        )
        update_results = await asyncio.gather(
            *[
                self.update_app_deployment(self.current_app_definitions.apps[app_name])
                for app_name in (added_apps | updated_apps)
            ]
        )
        uninstall_results = await asyncio.gather(
            *[
                self.uninstall_app(self.previous_app_definitions.apps[app_name])
                for app_name in removed_apps
            ]
        )
        await post_result_summary(
            self.current_app_definitions.name, update_results + uninstall_results
        )

    async def uninstall_app(self, app: App) -> UpdateAppResult:
        async with self.semaphore:
            logger.info(f"Uninstalling app {app.name!r}.")
            result = await run(
                f"helm uninstall {app.name} -n {app.values['namespace']}", suppress_errors=True
            )
            update_result = UpdateAppResult(app_name=app.name, **result)
            await post_result(app, self.current_app_definitions.name, update_result)
        return update_result

    async def update_app_deployment(self, app: App) -> Optional[UpdateAppResult]:
        app.set_value("deployment.labels.gitops/deploy_id", self.deploy_id)
        app.set_value("deployment.labels.gitops/status", github.STATUSES.in_progress)
        if github_deployment_url := app.values.get("github/deployment_url"):
            app.set_value("deployment.annotations.github/deployment_url", github_deployment_url)

        async with self.semaphore:
            logger.info(f"Deploying app {app.name!r}.")
            if app.chart.type == "git":
                async with temp_repo(
                    app.chart.git_repo_url, sha=app.chart.git_sha
                ) as chart_folder_path:
                    await run(f"cd {chart_folder_path}; helm dependency build")
                    with tempfile.NamedTemporaryFile(suffix=".yml") as cfg:
                        cfg.write(json.dumps(app.values).encode())
                        cfg.flush()
                        os.fsync(cfg.fileno())
                        result = await run(
                            "helm upgrade"
                            " --install"
                            " --timeout=600s"
                            f"{' --set skip_migrations=true' if self.skip_migrations else ''}"
                            f" -f {cfg.name}"
                            f" --namespace={app.values['namespace']}"
                            f" {app.name}"
                            f" {chart_folder_path}",
                            suppress_errors=True,
                        )
            elif app.chart.type == "helm":
                with tempfile.NamedTemporaryFile(suffix=".yml") as cfg:
                    cfg.write(json.dumps(app.values).encode())
                    cfg.flush()
                    os.fsync(cfg.fileno())
                    chart_version_arguments = (
                        f" --version={app.chart.version}" if app.chart.version else ""
                    )
                    await run(f"helm repo add {app.chart.helm_repo} {app.chart.helm_repo_url}")
                    result = await run(
                        "helm upgrade"
                        " --install"
                        " --timeout=600s"
                        f"{' --set skip_migrations=true' if self.skip_migrations else ''}"
                        f" -f {cfg.name}"
                        f" --namespace={app.values['namespace']}"
                        f" {app.name}"
                        f" {app.chart.helm_chart} {chart_version_arguments}",
                        suppress_errors=True,
                    )
            else:
                logger.warning("Local is not implemented yet")
                return None

            update_result = UpdateAppResult(app_name=app.name, **result)

            await post_result(app, self.current_app_definitions.name, update_result)
        return update_result

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
                    logger.info(f"Skipping changes in app {app_name!r}: marked inactive.")
                    continue
                updated.add(app_name)
        return added, updated, removed
