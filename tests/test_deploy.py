from asynctest import TestCase
from asynctest.mock import patch
from gitops_server.deploy import Deployer

from .sample_data import SAMPLE_GITHUB_PAYLOAD
from .utils import async_test


class DeployTests(TestCase):
    @patch('gitops_server.deploy.run')
    @async_test
    async def test_deployer(self, run_mock1):
        deployer = Deployer()
        await deployer.from_push_event(SAMPLE_GITHUB_PAYLOAD)
        await deployer.deploy()
        self.assertEqual(run_mock1.call_count, 1)
        self.assertRegex(
            run_mock1.call_args_list[0][0][0],
            r'helm upgrade --install --name=server0 -f .+\.yml'
            r' --namespace=test'
        )
