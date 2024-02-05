import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import gitops_server
import gitops_server.workers
from gitops_server.main import app

from .webhook_sample_data import headers, payload

client = TestClient(app)


def test_get_on_index_returns_200():
    response = client.get("/")

    assert response.status_code == 200


@patch("gitops_server.main.settings.GITHUB_WEBHOOK_KEY", "test_key")
def test_webhook_returns_200_if_hmac_is_correct():
    sha_encoding = hmac.new(b"test_key", json.dumps(payload).encode(), hashlib.sha1).hexdigest()
    headers["X-Hub-Signature"] = f"sha1={sha_encoding}"

    with patch.object(gitops_server.workers.DeployQueueWorker, "get_worker") as get_worker_mock:
        get_worker_mock.return_value = AsyncMock()
        response = client.post("/webhook", headers=headers, json=payload)

        assert response.status_code == 200
        get_worker_mock.assert_called()


@patch("gitops_server.main.settings.GITHUB_WEBHOOK_KEY", "test_key")
def test_webhook_returns_400_if_hmac_is_invalid():
    sha_encoding = "INVALID HMAC ENCODING"
    headers["X-Hub-Signature"] = f"sha1={sha_encoding}"

    with patch.object(gitops_server.workers.DeploymentStatusWorker, "get_worker", AsyncMock):
        response = client.post("/webhook", headers=headers, json=payload)

    assert response.status_code == 400
