import dataclasses
import json
import logging
import os
import urllib.request
from typing import Optional
from collections.abc import Iterable

import httpx

logger = logging.getLogger("gitops")


@dataclasses.dataclass
class SlackUser:
    name: str
    email: str
    real_name: str
    id: str

    def __str__(self) -> str:
        return f"<@{self.id}>"


class SlackGroup(SlackUser):
    def __str__(self) -> str:
        return f"<!subteam^{self.id}|{self.name}>"


async def post(message):
    """Post a message to a slack channel

    Uses the environment variable `SLACK_URL` to know which channel to post to.
    This URL is obtained by registering an integration with Slack.
    """
    logger.info("POSTING TO SLACK")
    url = os.environ["SLACK_URL"]
    data = {"text": message}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
        if response.status_code >= 300:
            logger.warning("Failed to post a message to slack (see below):")
            logger.error(f"{message}", exc_info=True)


def find_commiter_slack_user(name: str, email: str) -> Optional["SlackUser"]:
    token = os.environ.get("SLACK_TOKEN", "")
    if not token:
        return None

    with urllib.request.urlopen(
        urllib.request.Request(
            "https://slack.com/api/users.list?limit=300&pretty=1",
            headers={"Authorization": f"Bearer {token}"},
        )
    ) as response:
        data = json.loads(response.read())

    if not data["ok"]:
        raise Exception(data["error"])
    users = [
        SlackUser(
            m["name"].lower(),
            m["profile"].get("email", "").lower(),
            m.get("real_name", "").lower(),
            m["id"],
        )
        for m in data["members"]
        if not m["is_bot"]
    ]

    matched_user = search(name, email, users)
    return matched_user


def jaccard_similarity(x: Iterable, y: Iterable) -> float:
    """returns the jaccard similarity between two lists or strings"""
    intersection_cardinality = len(set.intersection(*[set(x), set(y)]))
    union_cardinality = len(set.union(*[set(x), set(y)]))
    return intersection_cardinality / float(union_cardinality)


def pairwise_tuples(x: str) -> list[tuple[str, str]]:
    """Given William returns [(W,i), (i,l), (l,l), (l,i), (i,a), (a, m)]"""
    if not x or len(x) < 2:
        return [("", "")]
    else:
        return [(letter, x[i + 1]) for i, letter in enumerate(x[:-1])]


def search(name: str, email: str, users: list[SlackUser]) -> SlackUser | None:
    def scoring_fn(user: SlackUser) -> float:
        return (
            jaccard_similarity(pairwise_tuples(user.email), pairwise_tuples(email))
            + jaccard_similarity(pairwise_tuples(name), pairwise_tuples(user.name))
            + jaccard_similarity(pairwise_tuples(name), pairwise_tuples(user.real_name))
        )

    matches = sorted([(scoring_fn(u), u) for u in users], key=lambda x: x[0], reverse=True)
    if matches[0][0] > 1.0:
        return matches[0][1]
    return None
