import asyncio
import logging
from pathlib import Path
from collections.abc import Callable

from ..types import RunOutput

logger = logging.getLogger("gitops.run")


async def _read_stream(stream: asyncio.StreamReader | None, cb: Callable[[bytes], None]) -> None:
    if stream is None:
        return
    while True:
        line = await stream.readline()
        if line:
            cb(line)
        else:
            break


async def run(command: str, suppress_errors: bool = False, cwd: str | Path | None = None) -> RunOutput:
    """Run a shell command.

    Runs the command in an asyncio executor to keep things async. Will
    optionally prevent raising an exception on failure with `suppress_errors`.
    """
    exit_code = 0
    logger.info(f'Running "{command}".')
    proc = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd
    )
    stdout, stderr = b"", b""

    def log_stdout(line: bytes) -> None:
        nonlocal stdout
        stdout += line
        logger.info(f"{line.decode()}")

    def log_stderr(line: bytes) -> None:
        nonlocal stderr
        stderr += line
        logger.info(f"{line.decode()}")

    await asyncio.gather(
        _read_stream(proc.stdout, log_stdout),
        _read_stream(proc.stderr, log_stderr),
    )

    await proc.communicate()
    exit_code = proc.returncode if proc.returncode not in (None, 128) else 1  # type: ignore
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
