import logging
import os
import tempfile
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from opentelemetry.trace import get_tracer

from . import run

tracer = get_tracer(__name__)

BASE_REPO_DIR = "/var/gitops/repos"

logger = logging.getLogger("gitops")


async def clone_repo(git_repo_url: str, path: str, sha: str | None = None):
    """Shallow Clones a git repo url to path and git-crypt unlocks all encrypted files"""
    logger.info(f'Cloning "{git_repo_url}".')

    url_with_oauth_token = git_repo_url.replace("://", f"://{os.environ['GITHUB_OAUTH_TOKEN'].strip()}@")

    with tracer.start_as_current_span("tempo_repo.clone_repo"):
        await run(f"git clone {url_with_oauth_token} {path}; cd {path}; git checkout {sha}")

    with tracer.start_as_current_span("temp_repo.git_crypt_unlock"):
        await run(f'cd {path}; git-crypt unlock {os.environ["GIT_CRYPT_KEY_FILE"]}')


@asynccontextmanager
async def temp_repo(git_repo_url: str, sha: str | None = None) -> AsyncGenerator[str, None]:
    """Checks out a git_repo_url to a temporary folder location. Returns temporary folder location"""
    with tracer.start_as_current_span("checkout_temp_repo"):
        with tempfile.TemporaryDirectory() as temporary_folder_path:
            await clone_repo(git_repo_url, path=temporary_folder_path, sha=sha)
            yield temporary_folder_path
