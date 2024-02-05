import logging
import os
import tempfile
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from . import run

BASE_REPO_DIR = "/var/gitops/repos"

logger = logging.getLogger("gitops")


async def clone_repo(git_repo_url: str, path: str, sha: str | None = None):
    """Shallow Clones a git repo url to path and git-crypt unlocks all encrypted files"""
    logger.info(f'Cloning "{git_repo_url}".')

    url_with_oauth_token = git_repo_url.replace("://", f"://{os.environ['GITHUB_OAUTH_TOKEN'].strip()}@")

    await run(f"git clone {url_with_oauth_token} {path}; cd {path}; git checkout {sha}")

    await run(f'cd {path}; git-crypt unlock {os.environ["GIT_CRYPT_KEY_FILE"]}')


@asynccontextmanager
async def temp_repo(git_repo_url: str, sha: str | None = None) -> AsyncGenerator[str, None]:
    """Checks out a git_repo_url to a temporary folder location. Returns temporary folder location"""
    with tempfile.TemporaryDirectory() as temporary_folder_path:
        await clone_repo(git_repo_url, path=temporary_folder_path, sha=sha)
        yield temporary_folder_path
