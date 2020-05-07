import yaml

from gitops_server.app_definitions import AppDefinitions
from gitops_server.namespace import Namespace


async def mock_load_app_definitions(self, url, sha):
    # Set different fg amounts for different sha's to mock a change to app_definitions
    if sha == 'bef04e58a0001234567890123456789012345678':
        fg = 4
    else:
        fg = 2
    app_definitions = AppDefinitions('mock-repo')
    app_definitions.namespaces = {
        'sample-app-1': Namespace('sample-ns-1', path=create_test_yaml(fg=fg)),
        'sample-app-2': Namespace('sample-ns-2', path=create_test_yaml(fg=fg)),
    }
    return app_definitions


def create_test_yaml(fg=4, bg=2):
    data = {
        'chart': 'https://github.com/some/chart',
        'images': {'template': 'template-tag-{tag}'},
        'namespace': 'mynamespace',
        'tags': ['tag1', 'tag2'],
        'image-tag': 'myimagetag',
        'containers': {'fg': {'replicas': fg}, 'bg': {'replicas': bg}},
        'environment': {
            'DJANGO_SETTINGS_MODULE': 'my.settings.module',
            'MEDIA_BUCKET': 'bucket-name',
            'MEDIA_BUCKET_PREFIX': '',
            'MEDIA_CLOUDINARY_PREFIX': 'cloudinaryprefix'
        }
    }
    with open('/tmp/deployment.yml', 'w+') as fh:
        fh.write(yaml.dump(data))

    data = {
        'secrets': {
            'SNAPE': 'KILLS_DUMBLEDORE',
            'DARTH_VADER': 'IS_LUKES_FATHER',
            'VERBAL': 'IS_KEYSER_SOZE',
        },
    }
    with open('/tmp/secrets.yml', 'w+') as fh:
        fh.write(yaml.dump(data))
    return '/tmp/'
