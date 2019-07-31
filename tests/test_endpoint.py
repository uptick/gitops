import json
from unittest import TestCase
from unittest.mock import patch

from gitops_server.main import app

from .sample_data import SAMPLE_GITHUB_PAYLOAD
from .utils import async_test


class EndpointTests(TestCase):
    @async_test
    def end_to_end_test(self):
        request, response = app.test_client.post('/webhook', data=json.dumps(SAMPLE_GITHUB_PAYLOAD))
        self.assertEqual(response.status, 200)
        # Do stuff with run_mock
