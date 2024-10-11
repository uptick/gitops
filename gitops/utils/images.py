from functools import lru_cache
from hashlib import md5

import boto3
import botocore
import botocore.exceptions
from colorama import Fore

from .cli import colourise

BATCH_SIZE = 100


def get_image(tag: str) -> str:
    """Finds a specific image in ECR."""
    # TODO
    raise NotImplementedError


@lru_cache
def get_latest_image(repository_name: str, prefix: str, ecr_repository: str | None = None) -> str | None:
    """Finds latest image in ECR with the given prefix and returns the image tag

    param ecr_repository is expected in this format: 305686791668.dkr.ecr.ap-southeast-2.amazonaws.com
    """
    describe_image_args = {}
    region_name = None
    if ecr_repository:
        describe_image_args["registryId"] = ecr_repository.split(".")[0]
        region_name = ecr_repository.split(".")[3]

    ecr_client = boto3.client("ecr", region_name=region_name)
    client_paginator = ecr_client.get_paginator("describe_images")

    results = []

    # First we try to find the image with `*latest`
    image_tag = f"{prefix}-latest" if prefix else "latest"


    def add_image_to_results(image):
        if prefix != "":
            if prefix_tags := [tag for tag in image["imageTags"] if tag.startswith(prefix + "-") and "latest" not in tag]:
                results.append((prefix_tags[0], image["imagePushedAt"]))
        else:
            if prefix_tags := [tag for tag in image["imageTags"] if "-" not in tag and "latest" not in tag]:
                results.append((prefix_tags[0], image["imagePushedAt"]))
    try:
        image = ecr_client.describe_images(
            repositoryName=repository_name,
            imageIds=[{"imageTag": image_tag}],
            **describe_image_args,
        )["imageDetails"][0]
        add_image_to_results(image)
    except botocore.exceptions.ClientError:
        # Ok we couldn't find the -latest image; lets scan images manually
        for ecr_response in client_paginator.paginate(
            repositoryName=repository_name,
            filter={
                "tagStatus": "TAGGED",
            },
            maxResults=BATCH_SIZE,
            **describe_image_args,
        ):
            for image in ecr_response["imageDetails"]:
                add_image_to_results(image)
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


def color_hash(bit: str) -> str:
    return [
        Fore.RED,
        Fore.GREEN,
        Fore.YELLOW,
        Fore.BLUE,
        Fore.MAGENTA,
        Fore.CYAN,
        Fore.WHITE,
    ][int.from_bytes(md5(bit.encode()).digest(), "big") % 7]  # noqa: S324
