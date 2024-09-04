import logging
import os

import httpx

logger = logging.getLogger("github")

GITHUB_OAUTH_TOKEN = os.environ.get("GITHUB_OAUTH_TOKEN")


class IssueNotFound(Exception): ...


class STATUSES:
    pending = "pending"  # default status when created during gh workflow
    in_progress = "in_progress"  # when helm installs
    success = "success"  # when helm deployed
    failure = "failure"  # when error during helm install
    error = "error"  # when error during helm deploy


def get_headers() -> dict:
    return {
        "Authorization": f"token {GITHUB_OAUTH_TOKEN}",
        "Content-Type": "application/json",
        "Accept": ("application/vnd.github.flash-preview+json, application/vnd.github.ant-man-preview+json"),
    }


async def update_deployment(deployment_url: str, status: str, description: str, environment_url=""):
    # https://docs.github.com/en/rest/reference/repos#create-a-deployment-status
    if not deployment_url:
        return
    status_url = deployment_url + "/statuses"
    logger.info(f"Updating deployment status of: {deployment_url} to {status}")
    async with httpx.AsyncClient() as client:
        data = {
            "state": status,
            "description": description,
            # https://github.com/chrnorm/deployment-status/issues/13
            "environment_url": environment_url,
        }
        response = await client.post(
            status_url,
            json=data,
            headers=get_headers(),
        )
        if response.status_code >= 300 and response.status_code != 404:
            try:
                logger.warn(response.json())
            except Exception:  # noqa
                logger.error("Something went wrong while logging the response for a failed deployment")
            logger.exception("Failed to update github deployment", exc_info=True, extra=response.__dict__)
