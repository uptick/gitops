from asynctest import TestCase
from asynctest.mock import patch
from gitops_server.deploy import Deployer

from .sample_data import SAMPLE_GITHUB_PAYLOAD
from .utils import mock_load_app_definitions

# Patch gitops_server.git.run & check correct commands + order
# Patch command that reads yaml from cluster repo +
# Provide x with a valid diff


class DeployTests(TestCase):
    @patch('gitops_server.deploy.run')
    @patch('gitops_server.deploy.post')
    @patch('gitops_server.deploy.Deployer.load_app_definitions', mock_load_app_definitions)
    @patch('gitops_server.deploy.temp_repo')
    async def test_deployer(self, temp_repo_mock, post_mock, run_mock):
        """Fake a deploy to two servers, bumping fg from 2 to 4."""
        run_mock.return_value = {'exit_code': 0, 'output': ''}
        temp_repo_mock.return_value.__aenter__.return_value = 'mock-repo'
        deployer = Deployer()
        await deployer.from_push_event(SAMPLE_GITHUB_PAYLOAD)
        await deployer.deploy()
        self.assertEqual(run_mock.call_count, 6)
        self.assertEqual(
            run_mock.call_args_list[0][0][0],
            'helm init --client-only',
        )
        self.assertEqual(
            run_mock.call_args_list[1][0][0],
            'cd mock-repo; helm dependency build'
        )
        self.assertRegex(
            run_mock.call_args_list[2][0][0],
            r'helm upgrade --install --timeout 600 -f .+\.yml'
            r' --namespace=mynamespace sample-app-\d mock-repo'
        )
        self.assertEqual(
            run_mock.call_args_list[3][0][0],
            'helm init --client-only',
        )
        self.assertEqual(
            run_mock.call_args_list[4][0][0],
            'cd mock-repo; helm dependency build'
        )
        self.assertRegex(
            run_mock.call_args_list[5][0][0],
            r'helm upgrade --install --timeout 600 -f .+\.yml'
            r' --namespace=mynamespace sample-app-\d mock-repo'
        )
        self.assertEqual(post_mock.call_count, 2)
        check_in_run_mock = [
            (0, 'mock-repo'), (0, 'authorusername'), (0, 'sample-app-1'), (0, 'sample-app-2'), (1, '2 succeeded'),
            (1, '0 failed'),
        ]
        for where, check in check_in_run_mock:
            self.assertIn(
                check,
                post_mock.call_args_list[where][0][0],
            )
