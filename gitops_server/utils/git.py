import asyncio
import logging
import os
import re
import tempfile
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from opentelemetry.trace import get_tracer

from . import run

tracer = get_tracer(__name__)
logger = logging.getLogger("gitops")

REPO_CACHE_DIR = Path("/tmp/gitops/repocache")
REPO_CACHE: dict[str, Path] = {}
repo_lock = asyncio.Semaphore(1)


async def clone_repo(git_repo_url: str, path: str, sha: str | None = None, branch: str | None = None):
    """Shallow Clones a git repo url to path and git-crypt unlocks all encrypted files"""
    logger.info(f'Cloning "{git_repo_url}".')

    url_with_oauth_token = git_repo_url.replace("://", f"://{os.environ['GITHUB_OAUTH_TOKEN'].strip()}@")

    with tracer.start_as_current_span("tempo_repo.clone_repo"):
        if sha:
            await run(f"git clone --depth 100 {url_with_oauth_token} {path}; cd {path}; git checkout {sha}")
        elif branch:
            await run(f"git clone --depth 1 {url_with_oauth_token} {path} --branch {branch}")
        else:
            await run(f"git clone --depth 100 {url_with_oauth_token} {path};")

    if GIT_CRYPT_KEY_FILE := os.environ.get("GIT_CRYPT_KEY_FILE"):
        with tracer.start_as_current_span("temp_repo.git_crypt_unlock"):
            await run(f"cd {path}; git-crypt unlock {GIT_CRYPT_KEY_FILE}")


def is_sha(sha_or_ref: str | None) -> bool:
    """Check if the given string is a valid SHA-1 hash or a short SHA."""
    if not sha_or_ref:
        return False
    return bool(re.fullmatch(r"[a-fA-F0-9]{4,40}", sha_or_ref))


@asynccontextmanager
async def temp_repo(git_repo_url: str, ref: str | None) -> AsyncGenerator[str, None]:
    """Checks out a git_repo_url to a temporary folder location. Returns temporary folder location"""
    # Someone passed us a branch name, not a sha

    if not is_sha(ref):
        async with temp_repo_branch(git_repo_url, branch=ref) as temp_repo_path:
            yield temp_repo_path
            return

    with tracer.start_as_current_span("checkout_temp_repo"):
        cache_path = REPO_CACHE_DIR / git_repo_url.split("/")[-1].split(".")[0]

        # Prep the repo cache
        if not (cache_path / ".git").exists():
            logger.info("Repo %s not in cache, cloning", git_repo_url)
            async with repo_lock:
                if cache_path.exists():
                    await run(f"rm -rf {cache_path}", suppress_errors=True)
                if not cache_path.exists():
                    cache_path.mkdir(parents=True)
                REPO_CACHE[git_repo_url] = cache_path
                await clone_repo(git_repo_url, path=str(cache_path))

        # Copy the repo cache to a temporary folder
        with tempfile.TemporaryDirectory() as temporary_folder_path:
            await run(f"rm -rf {temporary_folder_path}", suppress_errors=True)
            await run(f"cp -r {cache_path} {temporary_folder_path}")
            await run(f"cd {temporary_folder_path};git fetch; git checkout {ref}")

            yield temporary_folder_path


@asynccontextmanager
async def temp_repo_branch(git_repo_url: str, branch: str | None) -> AsyncGenerator[str, None]:
    """Checks out a git_repo_url to a temporary folder location. Returns temporary folder location"""
    with tracer.start_as_current_span("checkout_temp_repo_branch"):
        # Copy the repo cache to a temporary folder
        with tempfile.TemporaryDirectory() as temporary_folder_path:
            await clone_repo(git_repo_url, path=str(temporary_folder_path), branch=branch)
            yield temporary_folder_path
