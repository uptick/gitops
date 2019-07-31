from unittest import TestCase

from gitops_server.namespace import Namespace


def create_test_yaml():
    fh = open('/tmp/deployment.yml', 'w+')
    fh.write("""
chart: https://github.com/some/chart
images:
  template: template-tag-{tag}
namespace: mynamespace
tags:
  - tag1
  - tag2
image-tag: myimagetag
containers:
  fg:
    replicas: 4
  bg:
    replicas: 2
environment:
  DJANGO_SETTINGS_MODULE: my.settings.module
  MEDIA_BUCKET: bucket-name
  MEDIA_BUCKET_PREFIX: ''
  MEDIA_CLOUDINARY_PREFIX: cloudinaryprefix
""")
    fh.close()
    fh = open('/tmp/secrets.yml', 'w+')
    fh.write("""
secrets:
  SNAPE: KILLS_DUMBLEDORE
  DARTH_VADER: IS_LUKES_FATHER
  VERBAL: IS_KEYSER_SOZE
""")
    fh.close()
    return '/tmp/'


class MakeImageTests(TestCase):
    def test_direct_image(self):
        ns = Namespace('test')
        self.assertEqual(
            ns.make_image({'image': 'I0'}),
            'I0'
        )

    def test_image_tag(self):
        ns = Namespace(
            'test',
            deployments={
                'images': {
                    'template': 'image-template-{tag}'
                }
            }
        )
        self.assertEqual(
            ns.make_image({'image-tag': 'I0'}),
            'image-template-I0'
        )

    def test_image_tag_from_yaml(self):
        path = create_test_yaml()
        ns = Namespace('test', path)
        self.assertEqual(
            ns.values['image'],
            'template-tag-myimagetag'
        )

    def test_images_key_deleted(self):
        path = create_test_yaml()
        ns = Namespace('test', path)
        self.assertNotIn('images', ns.values)
