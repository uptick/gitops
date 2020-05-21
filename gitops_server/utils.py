import asyncio
import logging
import subprocess
from functools import partial

logger = logging.getLogger('gitops')


async def run(command, catch=False):
    """ Run a shell command.

    Runs the command in an asyncio executor to keep things async. Will
    optionally prevent raising an exception on failure with `catch`. Returns a
    dictionary containing `exit_code` and `output`.
    """
    loop = asyncio.get_event_loop()
    call = partial(
        sync_run,
        command,
        catch=catch
    )
    return await loop.run_in_executor(None, call)


def sync_run(command, catch=False):
    logger.info(f'Running "{command}".')
    exit_code = 0
    try:
        output = subprocess.check_output(
            command,
            shell=True,
            stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        if not catch:
            raise
        exit_code = e.returncode
        output = e.output
    return {
        'exit_code': exit_code,
        'output': output.decode()
    }


def get_repo_name_from_url(url):
    # https://github.com/user/repo-name.git > repo-name
    return url.split('/')[-1].split('.')[0]
