"""
This async worker keeps tracks of ongoing deployments by polling k8s space (CLUSTER_NAMESPACE).

The worker polls and checks for deployments with the following labels:  gitops/deploy_id   and  gitops/status=in_progress

Any failing/successfully deployed deployment is notified to github.
This mechanism will only work if the annotation: github/deployment_url is applied to the deployment.

TODO
- Update the slack summary message from deploy.py
- @notify the user if the deployment failed
"""

import asyncio
import logging

import kubernetes_asyncio  # type:ignore[import-untyped]
import kubernetes_asyncio.client  # type:ignore[import-untyped]
import kubernetes_asyncio.config  # type:ignore[import-untyped]

from gitops_server.settings import CLUSTER_NAMESPACE
from gitops_server.utils import github

logger = logging.getLogger("deployment_status")


async def get_ingress_url(api, namespace: str, app: str):
    """Attempts to get domain for the ingress associated with the app"""
    ingresses = await kubernetes_asyncio.client.NetworkingV1Api(api).list_namespaced_ingress(
        namespace=namespace, label_selector=f"app={app}"
    )
    environment_url = ""
    if ingresses.items:
        try:
            environment_url = "https://" + ingresses.items[0].spec.rules[0].host
        except Exception:
            logger.warning(f"Could not find ingress for {app=}")
    return environment_url


class DeploymentStatusWorker:
    """Watches for deployments and updates the github deployment status"""

    _worker = None

    @classmethod
    def get_worker(cls):
        if not cls._worker:
            loop = asyncio.get_running_loop()
            cls._worker = cls(loop)
        return cls._worker

    def __init__(self, loop):
        self.loop = loop

    async def load_config(self):
        try:
            kubernetes_asyncio.config.load_incluster_config()
        except kubernetes_asyncio.config.config_exception.ConfigException:
            await kubernetes_asyncio.config.load_kube_config()

    async def process_work(self):
        await asyncio.sleep(5)
        async with kubernetes_asyncio.client.ApiClient() as api:
            apps_api = kubernetes_asyncio.client.AppsV1Api(api)
            deployments = await apps_api.list_namespaced_deployment(
                # Only things that have gitops/deploy_id aka was deployed
                namespace=CLUSTER_NAMESPACE,
                label_selector="gitops/deploy_id,gitops/status=in_progress",
            )
            await asyncio.sleep(5)

            for deployment in deployments.items:
                # Deployment status may not exist yet
                if not deployment.status:
                    continue
                app = deployment.metadata.labels["app"]
                namespace = deployment.metadata.namespace
                github_deployment_url = deployment.metadata.annotations.get("github/deployment_url")
                conds = {}
                for x in deployment.status.conditions:
                    conds[x.type] = x
                status = None
                if (
                    len(conds) == 2
                    and conds["Available"].status == "True"
                    and conds["Progressing"].status == "True"
                    and conds["Progressing"].reason == "NewReplicaSetAvailable"
                ):
                    status = github.STATUSES.success
                    await github.update_deployment(
                        github_deployment_url,
                        status=status,
                        description="Deployed successfully",
                        environment_url=await get_ingress_url(api, namespace, app),
                    )
                elif (
                    "Progressing" in conds
                    and conds["Progressing"].status == "False"
                    and conds["Progressing"].reason == "ProgressDeadlineExceeded"
                ):
                    status = github.STATUSES.failure
                    await github.update_deployment(
                        github_deployment_url,
                        status=status,
                        description="Failed to deploy. Check the pod or migrations.",
                    )
                if status:
                    logger.info(f"Patching {deployment.metadata.name}.label.gitops/status to {status}")
                    patch = {"metadata": {"labels": {"gitops/status": status}}}
                    try:
                        await apps_api.patch_namespaced_deployment(
                            deployment.metadata.name, deployment.metadata.namespace, patch
                        )
                    except kubernetes_asyncio.client.exceptions.ApiException as e:
                        logger.warning(e, exc_info=True)

    async def run(self):
        logger.info("Starting deployment status watching loop")
        logger.info("Loading kubernetes asyncio api")
        while True:
            try:
                await self.load_config()
                await self.process_work()
            except Exception as e:
                logger.error(str(e), exc_info=True)
