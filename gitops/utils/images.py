from functools import lru_cache
from hashlib import md5

import boto3
from colorama import Fore

from .cli import colourise

BATCH_SIZE = 100


def get_image(tag):
    """Finds a specific image in ECR."""
    # TODO
    raise NotImplementedError


@lru_cache
def get_latest_image(repository_name: str, prefix: str) -> str:
    """Finds latest image in ECR with the given prefix and returns the image tag"""
    ecr_client = boto3.client("ecr")
    client_paginator = ecr_client.get_paginator("describe_images")

    results = []
    for ecr_response in client_paginator.paginate(
        repositoryName=repository_name,
        filter={"tagStatus": "TAGGED"},
        maxResults=BATCH_SIZE,
    ):
        for image in ecr_response["imageDetails"]:
            if prefix != "":
                if prefix_tags := [
                    tag for tag in image["imageTags"] if tag.startswith(prefix + "-")
                ]:
                    results.append((prefix_tags[0], image["imagePushedAt"]))
            else:
                if prefix_tags := [tag for tag in image["imageTags"] if "-" not in tag]:
                    results.append((prefix_tags[0], image["imagePushedAt"]))

    if not results:
        if prefix:
            print(f'No images found in repository: {repository_name} with tag "{prefix}-*".')
        else:
            print(f"No images found in repository: {repository_name}")
        return None

    latest_image_tag = sorted(results, key=lambda image: image[1], reverse=True)[0][0]
    return latest_image_tag


def colour_image(image_tag: str) -> str:
    if not image_tag:
        return image_tag

    bits = image_tag.split("-")
    if len(bits) > 1:
        bits[0] = colourise(bits[0], color_hash(bits[1]))
        return "-".join(bits)
    else:
        return colourise(bits[0], color_hash(bits[0]))


def color_hash(bit):
    return [
        Fore.RED,
        Fore.GREEN,
        Fore.YELLOW,
        Fore.BLUE,
        Fore.MAGENTA,
        Fore.CYAN,
        Fore.WHITE,
    ][int.from_bytes(md5(bit.encode()).digest(), "big") % 7]
