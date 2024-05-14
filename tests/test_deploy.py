import re
from unittest.mock import patch

import pytest

from gitops.common.app import App
from gitops_server.workers.deployer import Deployer

from .sample_data import SAMPLE_GITHUB_PAYLOAD, SAMPLE_GITHUB_PAYLOAD_SKIP_MIGRATIONS
from .utils import mock_load_app_definitions

# Patch gitops_server.git.run & check correct commands + order
# Patch command that reads yaml from cluster repo +
# Provide x with a valid diff


@pytest.mark.asyncio
class TestDeploy:
    @patch("gitops_server.workers.deployer.deploy.run")
    @patch("gitops_server.utils.slack.post")
    @patch("gitops_server.workers.deployer.deploy.load_app_definitions", mock_load_app_definitions)
    @patch("gitops_server.workers.deployer.deploy.temp_repo")
    async def test_deployer_git(self, temp_repo_mock, post_mock, run_mock):
        """Fake a deploy to two servers, bumping fg from 2 to 4."""
        run_mock.return_value = {"exit_code": 0, "output": ""}
        temp_repo_mock.return_value.__aenter__.return_value = "mock-repo"
        deployer = await Deployer.from_push_event(SAMPLE_GITHUB_PAYLOAD)
        await deployer.deploy()
        assert run_mock.call_count == 4
        assert run_mock.call_args_list[0][0][0] == "cd mock-repo; helm dependency build"
        assert re.match(
            r"helm secrets upgrade --create-namespace --install --timeout=600s -f .+\.yml"
            r" --namespace=mynamespace sample-app-\d mock-repo",
            run_mock.call_args_list[1][0][0],
        )
        assert run_mock.call_args_list[2][0][0] == "cd mock-repo; helm dependency build"
        assert re.match(
            r"helm secrets upgrade --create-namespace --install --timeout=600s -f .+\.yml"
            r" --namespace=mynamespace sample-app-\d mock-repo",
            run_mock.call_args_list[3][0][0],
        )
        assert post_mock.call_count == 2
        check_in_run_mock = [
            (0, "mock-repo"),
            (0, "Author Fullname"),
            (0, "sample-app-1"),
            (0, "sample-app-2"),
            (1, "2 succeeded"),
            (1, "0 failed"),
        ]
        for where, check in check_in_run_mock:
            assert check in post_mock.call_args_list[where][0][0]

    @patch("gitops_server.workers.deployer.deploy.run")
    @patch("gitops_server.workers.deployer.deploy.post_result")
    @patch("gitops_server.workers.deployer.deploy.load_app_definitions", mock_load_app_definitions)
    @patch("gitops_server.workers.deployer.deploy.temp_repo")
    async def test_deployer_update_helm_app(self, temp_repo_mock, post_mock, run_mock):
        run_mock.return_value = {"exit_code": 0, "output": ""}
        helm_app = App(
            "helm_app",
            deployments={
                "chart": {
                    "type": "helm",
                    "helm_repo_url": "https://helm.charts",
                    "helm_chart": "brigade/brigade",
                    "helm_repo": "brigade",
                },
                "namespace": "mynamespace",
                "tags": ["tag1", "tag2"],
                "cluster": "UNKNOWN",
            },
        )

        deployer = await Deployer.from_push_event(SAMPLE_GITHUB_PAYLOAD)
        await deployer.update_app_deployment(helm_app)

        assert run_mock.call_count == 2
        assert run_mock.call_args_list[0][0][0] == "helm repo add brigade https://helm.charts"
        assert re.match(
            r"helm secrets upgrade --create-namespace --install --timeout=600s -f .+\.yml"
            r" --namespace=mynamespace helm_app brigade/brigade",
            run_mock.call_args_list[1][0][0],
        )
        assert post_mock.call_count == 1

    @patch("gitops_server.workers.deployer.deploy.run")
    @patch("gitops_server.utils.slack.post")
    @patch("gitops_server.workers.deployer.deploy.load_app_definitions", mock_load_app_definitions)
    @patch("gitops_server.workers.deployer.deploy.temp_repo")
    async def test_deployer_skip_migrations_in_commit_message_should_run_helm_without_hooks(
        self, temp_repo_mock, post_mock, run_mock
    ):
        """Fake a deploy to two servers, bumping fg from 2 to 4."""
        run_mock.return_value = {"exit_code": 0, "output": ""}
        temp_repo_mock.return_value.__aenter__.return_value = "mock-repo"
        deployer = await Deployer.from_push_event(SAMPLE_GITHUB_PAYLOAD_SKIP_MIGRATIONS)
        await deployer.deploy()
        assert run_mock.call_count == 4
        assert run_mock.call_args_list[0][0][0] == "cd mock-repo; helm dependency build"
        assert re.match(
            r"helm secrets upgrade --create-namespace --install --timeout=600s --set skip_migrations=true -f .+\.yml"
            r" --namespace=mynamespace sample-app-\d mock-repo",
            run_mock.call_args_list[1][0][0],
        )
        assert run_mock.call_args_list[2][0][0] == "cd mock-repo; helm dependency build"
        assert re.match(
            r"helm secrets upgrade --create-namespace --install --timeout=600s --set skip_migrations=true -f .+\.yml"
            r" --namespace=mynamespace sample-app-\d mock-repo",
            run_mock.call_args_list[3][0][0],
        )
        assert post_mock.call_count == 2
        check_in_run_mock = [
            (0, "mock-repo"),
            (0, "Author Fullname"),
            (0, "sample-app-1"),
            (0, "sample-app-2"),
            (1, "2 succeeded"),
            (1, "0 failed"),
        ]
        for where, check in check_in_run_mock:
            assert check in post_mock.call_args_list[where][0][0]
