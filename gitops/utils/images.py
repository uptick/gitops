from colorama import Fore
from contextlib import suppress
from hashlib import md5

import boto3

from .cli import colourise

PREFIX_CACHE = {}


def get_image(tag):
    """ Finds a specific image in ECR. """
    # TODO
    raise NotImplementedError


def get_latest_image(prefix):
    """ Finds latest image in ECR with the given prefix. """
    with suppress(KeyError):
        return PREFIX_CACHE[prefix]

    ecr = boto3.client('ecr')
    image_tags = []
    next_token = None
    while True:
        opts = {
            'repositoryName': 'uptick',
            'filter': {'tagStatus': 'TAGGED'}
        }
        if next_token:
            opts['nextToken'] = next_token
        results = ecr.list_images(**opts)
        for image in results['imageIds']:
            if image['imageTag'].startswith(prefix + '-'):
                image_tags.append(image['imageTag'])
        next_token = results.get('nextToken')
        if not next_token:
            break
    if not image_tags:
        print(f'No images with tag "{prefix}-*".')
        PREFIX_CACHE[prefix] = None
        return None
    results = ecr.describe_images(
        repositoryName='uptick',
        imageIds=[{'imageTag': t} for t in image_tags],
        filter={'tagStatus': 'TAGGED'}
    )
    results = [
        (i['imagePushedAt'], i['imageTags'][0])
        for i in results['imageDetails']
    ]
    results = sorted(results, key=lambda x: x[0], reverse=True)
    latest_image_tag = results[0][1]
    PREFIX_CACHE[prefix] = latest_image_tag
    return latest_image_tag


def colour_image(image_tag):
    bits = image_tag.split('-')
    bits[0] = colourise(bits[0], color_hash(bits[1]))
    return '-'.join(bits)


def color_hash(bit):
    return [
        Fore.RED,
        Fore.GREEN,
        Fore.YELLOW,
        Fore.BLUE,
        Fore.MAGENTA,
        Fore.CYAN,
        Fore.WHITE,
    ][int.from_bytes(md5(bit.encode()).digest(), 'big') % 7]
