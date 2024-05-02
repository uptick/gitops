from collections.abc import Iterable

from colorama import Fore

from .cli import colourise

TAG_ORDER = [
    "workforce",
    "maintenance",
    "compliance",
    "customer",
    "internal",
    "sandbox",
    "production",
    "enterprise",
    "multitenanted",
    "workspace_group",
    "dedicated",
    "preview",
    "onboardng",
    "fast_release",
    "slow_release",
    "inactive",
]

TAG_COLOURS = {
    "workforce": Fore.LIGHTGREEN_EX,
    "maintenance": Fore.LIGHTMAGENTA_EX,
    "compliance": Fore.BLUE,
    "customer": Fore.LIGHTBLUE_EX,
    "internal": Fore.LIGHTCYAN_EX,
    "sandbox": Fore.LIGHTYELLOW_EX,
    "multitenanted": Fore.LIGHTBLUE_EX,
    "workspace_group": Fore.LIGHTYELLOW_EX,
    "production": Fore.LIGHTRED_EX,
    "enterprise": Fore.WHITE,
    "dedicated": Fore.WHITE,
    "fast_release": Fore.YELLOW,
    "slow_release": Fore.MAGENTA,
    "inactive": Fore.RED,
}


def validate_tags(tags: Iterable[str], other_valid_tags: Iterable[str]) -> None:
    unrecognised_tags = set(tags) - set(TAG_COLOURS.keys()) - set(other_valid_tags)
    if unrecognised_tags:
        raise Exception(f"Unrecognised tags: {', '.join(unrecognised_tags)}")


def colour_tag(tag: str) -> str:
    try:
        return colourise(tag, TAG_COLOURS[tag])
    except KeyError:
        return colourise(tag, Fore.LIGHTBLACK_EX)


def colour_tags(tags: Iterable[str]) -> str:
    return ", ".join(map(colour_tag, tags))


def sort_tags(tags: list[str]) -> list[str]:
    result = []
    for t in TAG_ORDER:
        if t in tags:
            result.append(t)
            tags.remove(t)
    return result + sorted(tags)
