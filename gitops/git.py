import logging
import os
import tempfile
from contextlib import contextmanager

from .utils import run

BASE_REPO_DIR = '/var/gitops/repos'

logger = logging.getLogger('gitops')


def get_repo_path(name):
    path = os.path.join(BASE_REPO_DIR, name)
    os.makedirs(path, exist_ok=True)
    return path


def clone_repo(name, url, path):
    logger.info(f'Cloning "{name}" from "{url}".')
    run((
        'git clone {url} {path}'
    ).format(
        path=path,
        url=url
    ))
    run((
        'cd {path}; '
        'git-crypt unlock {key}'
    ).format(
        path=path,
        key=os.environ['GIT_CRYPT_KEY_FILE']
    ))


def update_repo(name, url, path):
    logger.info('PULL: {name}')
    run((
        'cd {path}; '
        'git pull {url}'
    ).format(
        path=path,
        url=url
    ))


def checkout_repo_sha(name, sha, path):
    logger.info(f'Checkout "{name}" at "{sha}".')
    run((
        'cd {path}; '
        'git checkout {sha}'
    ).format(
        path=path,
        sha=sha
    ))


def refresh_repo(name, url, sha=None, path=None):
    if not path:
        path = get_repo_path(name)
    if not os.path.exists(path):
        update_repo(name, url, path)
    else:
        clone_repo(name, url, path)
    if sha:
        checkout_repo_sha(name, sha, path)


@contextmanager
def temp_repo(url, name=None, sha=None):
    if not name:
        name = 'anonymous'
    with tempfile.TemporaryDirectory() as tmp:
        if not isinstance(tmp, str):
            tmp = tmp.name
        refresh_repo(name, url, sha=sha, path=tmp)
        yield tmp
