"""Overwrite this file in kubernetes to inject custom code"""

import logging
import os

import httpx
from opentelemetry import trace

from gitops.common.app import App
from gitops_server import settings
from gitops_server.types import UpdateAppResult
from gitops_server.utils import github
from gitops_server.utils.slack import SlackGroup, SlackUser, find_commiter_slack_user

tracer = trace.get_tracer(__name__)

logger = logging.getLogger(__name__)


async def update_issue_from_deployment_url(
    app: App,
    deployment_url: str,
) -> None:
    async with httpx.AsyncClient() as client:
        headers = github.get_headers()
        deployment_response = await client.get(deployment_url, headers=headers)
        try:
            sha = deployment_response.json().get("sha", "")
            issues_response = await client.get(f"https://api.github.com/search/issues?q={sha}+is:pr", headers=headers)
            issue_url = issues_response.json()["items"][0]["url"]
        except Exception:
            logging.warning(f"Could not find issue for {app.name}")
            return

        try:
            response = await client.post(issue_url + "/labels", json={"labels": ["NODEPLOY"]}, headers=headers)
            response.raise_for_status()
            comment = (
                ":poop: Failed to deploy :poop:\n Applying `NODEPLOY` label to shutdown the server"
                " and prevent deploys until it has been fixed.\nCheck migration logs at"
                f" https://my.papertrailapp.com/systems/{app.name}-migration/events"
            )
            response = await client.post(issue_url + "/comments", json={"body": comment}, headers=headers)
            response.raise_for_status()
        except Exception:
            logging.warning("Failed to update PR")
            return


async def handle_successful_deploy(
    app: App,
    result,
    deployer,
) -> UpdateAppResult:
    github_deployment_url = str(app.values.get("github/deployment_url", ""))
    await github.update_deployment(
        github_deployment_url,
        status=github.STATUSES.in_progress,
        description="Helm installed app into cluster. Waiting for pods to deploy.",
    )
    return result


DEFAULT_USER_GROUP = SlackGroup("devops", "", "devops", os.environ.get("DEFAULT_SLACK_USER_GROUP_ID", "S5KVCGSGP"))


async def handle_failed_deploy(app: App, result: UpdateAppResult, deployer) -> UpdateAppResult:
    github_deployment_url = str(app.values.get("github/deployment_url", ""))
    if github_deployment_url:
        await github.update_deployment(
            github_deployment_url,
            status=github.STATUSES.failure,
            description=f"Failed to deploy app. {result['output']}",
        )
        await update_issue_from_deployment_url(app, github_deployment_url)

    email = deployer.author_email

    if "devops" in email.lower() or "tickforge" in email.lower():
        slack_user: SlackGroup | SlackUser = DEFAULT_USER_GROUP
    else:
        slack_user = (
            await find_commiter_slack_user(name=deployer.author_name, email=deployer.author_email) or DEFAULT_USER_GROUP
        )
    slack_user_msg = f" {slack_user} " if slack_user else ""
    log_msg = f"<https://my.papertrailapp.com/systems/{app.name}-migration/events|(Migration Logs)>"
    result["slack_message"] = (
        f"Failed to deploy app `{result['app_name']}` for cluster"
        f" `{settings.CLUSTER_NAME}` :rotating_light:"
        f" {slack_user_msg} {log_msg}:\n>>>{result['output']}\n"
    )
    return result
