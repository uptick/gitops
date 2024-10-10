from typing import Any

import yaml

from gitops.common.app import App
from gitops_server.types import AppDefinitions


async def mock_load_app_definitions(url, sha):
    # Set different fg amounts for different sha's to mock a change to app_definitions
    if sha == "bef04e58a0001234567890123456789012345678":
        fg = 4
    else:
        fg = 2
    app_definitions = AppDefinitions(
        "mock-repo",
        apps={
            "sample-app-1": App("sample-app-1", path=create_test_yaml(fg=fg)),
            "sample-app-2": App("sample-app-2", path=create_test_yaml(fg=fg)),
        },
    )
    return app_definitions


def create_test_yaml(fg=4, bg=2, **kwargs: Any):
    data = {
        "chart": "https://github.com/some/chart",
        "images": {"template": "template-tag-{tag}"},
        "namespace": "mynamespace",
        "tags": ["tag1", "tag2"],
        "image-tag": "myimagetag",
        "cluster": "test-cluster",
        "containers": {"fg": {"replicas": fg}, "bg": {"replicas": bg}},
        "environment": {
            "DJANGO_SETTINGS_MODULE": "my.settings.module",
            "MEDIA_BUCKET": "bucket-name",
            "MEDIA_BUCKET_PREFIX": "",
            "MEDIA_CLOUDINARY_PREFIX": "cloudinaryprefix",
        },
    }

    for k, v in kwargs.items():
        data[k] = v

    with open("/tmp/deployment.yml", "w+") as fh:
        fh.write(yaml.dump(data))

    data = {
        "secrets": {
            "SNAPE": "KILLS_DUMBLEDORE",
            "DARTH_VADER": "IS_LUKES_FATHER",
            "VERBAL": "IS_KEYSER_SOZE",
        },
    }
    with open("/tmp/secrets.yml", "w+") as fh:
        fh.write(yaml.dump(data))
    return "/tmp/"


# def create_test_kubeconfig():
#     data = {
#         'apiVersion': 'v1',
#         'clusters': [
#             {
#                 'cluster': {
#                     'certificate-authority-data': 'XXX',
#                     'server': 'https://XXX.elb.amazonaws.com',
#                 },
#                 'name': 'testcluster',
#             },
#         ],
#         'contexts': [
#             {
#                 'context': {
#                     'cluster': 'testcluster',
#                     'user': 'testuser',
#                 },
#                 'name': 'testcontext',
#             },
#         ],
#         'current-context': 'testcontext',
#         'kind': 'Config',
#         'preferences': {},
#         'users': [
#             {
#                 'name': 'testuser',
#                 'user': {},
#             },
#         ],
#     }
#     with open('/tmp/kubeconfig', 'w+') as fh:
#         fh.write(yaml.dump(data))
#     return '/tmp/'
