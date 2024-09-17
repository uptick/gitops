import asyncio
import logging
import os
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


async def clone_repo(git_repo_url: str, path: str, sha: str | None = None):
    """Shallow Clones a git repo url to path and git-crypt unlocks all encrypted files"""
    logger.info(f'Cloning "{git_repo_url}".')

    url_with_oauth_token = git_repo_url.replace("://", f"://{os.environ['GITHUB_OAUTH_TOKEN'].strip()}@")

    with tracer.start_as_current_span("tempo_repo.clone_repo"):
        if sha:
            await run(f"git clone --depth 100 {url_with_oauth_token} {path}; cd {path}; git checkout {sha}")
        else:
            await run(f"git clone --depth 100 {url_with_oauth_token} {path};")

    with tracer.start_as_current_span("temp_repo.git_crypt_unlock"):
        await run(f'cd {path}; git-crypt unlock {os.environ["GIT_CRYPT_KEY_FILE"]}')


@asynccontextmanager
async def temp_repo(git_repo_url: str, sha: str | None = None) -> AsyncGenerator[str, None]:
    """Checks out a git_repo_url to a temporary folder location. Returns temporary folder location"""
    with tracer.start_as_current_span("checkout_temp_repo"):
        cache_path = REPO_CACHE_DIR / git_repo_url.split("/")[-1].split(".")[0]
        if not (cache_path / ".git").exists():
            logger.info("Repo %s not in cache, cloning", git_repo_url)
            async with repo_lock:
                if cache_path.exists():
                    await run(f"rm -rf {cache_path}", suppress_errors=True)
                if not cache_path.exists():
                    cache_path.mkdir(parents=True)
                REPO_CACHE[git_repo_url] = cache_path
                await clone_repo(git_repo_url, path=str(cache_path))
        with tempfile.TemporaryDirectory() as temporary_folder_path:
            await run(f"rm -rf {temporary_folder_path}", suppress_errors=True)
            await run(f"cp -r {cache_path} {temporary_folder_path}")
            await run(f"cd {temporary_folder_path};git fetch; git checkout {sha}")
            yield temporary_folder_path
