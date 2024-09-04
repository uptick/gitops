import asyncio
import logging

from ..types import RunOutput

logger = logging.getLogger("gitops")


async def run(command, suppress_errors=False) -> RunOutput:
    """Run a shell command.

    Runs the command in an asyncio executor to keep things async. Will
    optionally prevent raising an exception on failure with `suppress_errors`.
    """
    exit_code = 0
    logger.info(f'Running "{command}".')
    proc = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()
    exit_code = proc.returncode or 1
    if exit_code == 0:
        return RunOutput(exit_code=exit_code, output=stdout.decode())
    else:
        # Something went wrong.
        if not suppress_errors:
            raise Exception(f"Run: {command} returned with exit code: {exit_code}\n\n{stderr.decode()}")
        return RunOutput(exit_code=exit_code, output=stderr.decode())


def get_repo_name_from_url(url: str):
    # https://github.com/user/repo-name.git > repo-name
    return url.split("/")[-1].split(".")[0]
