import os
import tempfile
from contextlib import asynccontextmanager

import pytest

from gitops_server.utils import git, run

os.environ["GITHUB_OAUTH_TOKEN"] = ""


@asynccontextmanager
async def make_dummy_repo():
    with tempfile.TemporaryDirectory() as temporary_folder_path:
        if os.environ.get("CI"):
            await run("git config --global user.email 'you@example.com'")
            await run("git config --global user.name 'Your Name'")
            await run("git config --global init.defaultBranch main")
        await run("git init", cwd=temporary_folder_path)
        for _ in range(10):
            await run("git commit -m 'temporary commit' --allow-empty", cwd=temporary_folder_path)
        await run("git checkout -b 'test'", cwd=temporary_folder_path)
        for _ in range(10):
            await run("git commit -m 'temporary commit' --allow-empty", cwd=temporary_folder_path)
        await run("git checkout main", cwd=temporary_folder_path)
        yield temporary_folder_path


@pytest.mark.asyncio
class TestGit:
    async def test_temp_repo_with_branch(self):
        async with make_dummy_repo() as test_repo:
            async with git.temp_repo(test_repo, ref="test"):
                pass

            async with git.temp_repo(test_repo, ref="main"):
                pass

    async def test_temp_repo_with_no_ref(self):
        async with make_dummy_repo() as test_repo:
            async with git.temp_repo(test_repo, ref=None):
                pass

    async def test_temp_repo_with_sha(self):
        async with make_dummy_repo() as test_repo:
            sha = (await run("git rev-parse HEAD", cwd=test_repo))["output"].strip()
            assert git.is_sha(sha)

            async with git.temp_repo(test_repo, ref=sha):
                pass
