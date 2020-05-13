import logging
import os
import tempfile
from contextlib import asynccontextmanager

from .utils import run

BASE_REPO_DIR = '/var/gitops/repos'

logger = logging.getLogger('gitops')


def get_repo_path(name):
    path = os.path.join(BASE_REPO_DIR, name)
    os.makedirs(path, exist_ok=True)
    return path


def inject_oauth_token(url):
    ii = url.index('://') + 3
    return url[:ii] + os.environ['GITHUB_OAUTH_TOKEN'] + '@' + url[ii:]


async def clone_repo(name, url, path):
    # TODO: Don't log the oauth token.
    url = inject_oauth_token(url)
    logger.info(f'Cloning "{name}" from "{url}".')
    await run(f'git clone {url} {path}')
    await run(f'cd {path}; git-crypt unlock {os.environ["GIT_CRYPT_KEY_FILE"]}')


async def update_repo(name, url, path):
    logger.info('PULL: {name}')
    await run(f'cd {path}; git pull {url}')


async def checkout_repo_sha(name, sha, path):
    logger.info(f'Checkout "{name}" at "{sha}".')
    await run(f'cd {path}; git checkout {sha}')


async def refresh_repo(name, url, sha=None, path=None):
    if not path:
        path = get_repo_path(name)
    if not os.path.exists(path):
        await update_repo(name, url, path)
    else:
        await clone_repo(name, url, path)
    if sha:
        await checkout_repo_sha(name, sha, path)


@asynccontextmanager
async def temp_repo(url, name=None, sha=None):
    if not name:
        name = 'anonymous'
    with tempfile.TemporaryDirectory() as tmp:
        if not isinstance(tmp, str):
            tmp = tmp.name
        await refresh_repo(name, url, sha=sha, path=tmp)
        yield tmp
