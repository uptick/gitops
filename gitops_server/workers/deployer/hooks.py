"""Overwrite this file in kubernetes to inject custom code"""
import logging

import httpx

from gitops.common.app import App
from gitops_server.types import UpdateAppResult
from gitops_server.utils import github

logger = logging.getLogger(__name__)


async def update_issue_from_deployment_url(app: App, deployment_url: str, **kwargs) -> None:
    if "qa" not in app.name:
        return
    async with httpx.AsyncClient() as client:
        headers = github.get_headers()
        deployment_response = await client.get(deployment_url, headers=headers)
        sha = deployment_response.json()["sha"]

        try:
            issues_response = await client.get(
                f"https://api.github.com/search/issues?q={sha}+is:pr", headers=headers
            )
            issue_url = issues_response.json()["items"][0]["url"]
        except Exception:
            logging.warning("Could not find issue", exc_info=True)
            return

        try:
            response = await client.post(
                issue_url + "/labels", json={"labels": ["NODEPLOY"]}, headers=headers
            )
            response.raise_for_status()
            comment = (
                ":poop: Failed to deploy :poop:\n Applying `NODEPLOY` label to shutdown the server"
                " and prevent deploys until it has been fixed.\nCheck migration logs at"
                f" https://my.papertrailapp.com/systems/{app.name}-migration/events"
            )
            response = await client.post(
                issue_url + "/comments", json={"body": comment}, headers=headers
            )
            response.raise_for_status()
        except Exception:
            logging.warning("Failed to update PR")
            return


async def handle_successful_deploy(app: App, result, **kwargs) -> UpdateAppResult:
    github_deployment_url = str(app.values.get("github/deployment_url", ""))
    await github.update_deployment(
        github_deployment_url,
        status=github.STATUSES.in_progress,
        description="Helm installed app into cluster. Waiting for pods to deploy.",
    )
    return result


async def handle_failed_deploy(app: App, result: UpdateAppResult, **kwargs) -> UpdateAppResult:
    github_deployment_url = str(app.values.get("github/deployment_url", ""))
    if github_deployment_url:

        await github.update_deployment(
            github_deployment_url,
            status=github.STATUSES.failure,
            description=f"Failed to deploy app. {result['output']}",
        )
        await update_issue_from_deployment_url(github_deployment_url)

    result.output += (
        f"\n Check logs here: https://my.papertrailapp.com/systems/{app.name}-migration/events"
    )

    return result
