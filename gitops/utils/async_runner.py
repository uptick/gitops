import asyncio
import curses
from .cli import success, warning, progress


def init_curses():
    stdscr = curses.initscr()
    curses.start_color()
    curses.use_default_colors()
    # -1 is default terminal background color
    curses.init_pair(1, curses.COLOR_RED, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.noecho()
    curses.cbreak()
    # Turn off cursor
    curses.curs_set(0)
    return stdscr


async def run_tasks_async_with_progress(tasks):
    stdscr = init_curses()
    stdscr.addstr(0, 0, 'Your command is now running on the following servers:')
    # Ugly.
    just = len(max(tasks, key=lambda x: len(x[1]))[1]) + 1
    tasks = [print_async_complete(task, num + 1, len(tasks), just, stdscr) for num, task in enumerate(tasks)]
    outputs = await asyncio.gather(*tasks)
    stdscr.addstr(len(tasks) + 1, 0, 'Done. Press enter to view the outputs of the commands.')
    stdscr.refresh()
    curses.echo()
    curses.nocbreak()
    input()
    curses.endwin()
    print("\n".join(outputs))


async def print_async_complete(task, position, length, just, stdscr):
    """
    Move cursor to `position`, print task name, run  task coroutine, then move
    back to `pos` print message and a justified completion mark (red cross or
    green check) depending on if the coroutine raises an exception or not.
    """
    cor, name = task
    stdscr.addstr(position, 0, name)
    stdscr.refresh()
    output = f'{"-"*20}\n{progress(name)}\n{"-"*20}\n'
    try:
        output += await cor
    except Exception as e:
        stdscr.addstr(position, just, '✗', curses.color_pair(1))
        output += f'Exception: {str(e)}'
    else:
        stdscr.addstr(position, just, '✔', curses.color_pair(2))
    stdscr.refresh()
    return output


async def async_run(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()
    return (
        stdout,
        stderr,
        (
            success('[stdout]\n')
            + f'{stdout.decode()}\n'
            + warning('[stderr]\n')
            + f'{stderr.decode()}\n'
        )
    )
