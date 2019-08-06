from unittest import TestCase

from gitops_server.namespace import Namespace

from .utils import create_test_yaml


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
