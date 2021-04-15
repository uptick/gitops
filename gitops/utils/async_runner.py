import asyncio
import curses

from .cli import progress, success, warning


def init_curses(num_tasks):
    stdscr = curses.initscr()
    height, width = stdscr.getmaxyx()
    win = curses.newpad(num_tasks, 300)
    curses.start_color()
    curses.use_default_colors()
    # -1 is default terminal background color
    curses.init_pair(1, curses.COLOR_RED, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.noecho()
    curses.cbreak()
    # Turn off cursor
    curses.curs_set(0)
    return (win, height, width)


def addstr(win_info, x, y, text, color=0):
    win, height, width = win_info
    win.addstr(x, y, text, color)
    win.clrtoeol()
    win.clearok(1)
    win.refresh(0, 0, 0, 0, height - 1, width - 1)


async def run_tasks_async_with_progress(tasks, max_concurrency=10):
    sem = asyncio.Semaphore(max_concurrency)
    win_info = init_curses(len(tasks) + 1)
    addstr(win_info, 0, 0, f'Your command is now running on the following {len(tasks)} servers (may extend off bottom of terminal):')
    # Ugly.
    just = len(max(tasks, key=lambda x: len(x[1]))[1]) + 1
    tasks = [print_async_complete(task, num + 1, just, win_info, sem) for num, task in enumerate(tasks)]
    # Can reverse tasks with [::-1] if we prefer them to run bottom to top on output.
    outputs = await asyncio.gather(*tasks, return_exceptions=True)
    addstr(win_info, 0, 0, 'Done. Press enter to print the outputs of the commands.')
    curses.echo()
    curses.nocbreak()
    input()
    curses.endwin()
    print("\n".join(outputs))


async def print_async_complete(task, position, just, win_info, sem):
    cor, name = task
    addstr(win_info, position, 0, name)
    output = f'{"-"*20}\n{progress(name)}\n{"-"*20}\n'
    try:
        await sem.acquire()
        output += await cor
    except Exception as e:
        addstr(win_info, position, just, '✗', curses.color_pair(1))
        output += f'Exception: {str(e)}'
    else:
        addstr(win_info, position, just, '✔', curses.color_pair(2))
    sem.release()
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
