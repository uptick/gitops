from unittest import TestCase

from gitops_server.app_definitions import App

from .utils import create_test_yaml


class MakeImageTests(TestCase):
    def test_direct_image(self):
        app = App('test')
        self.assertEqual(app.make_image({'image': 'I0'}), 'I0')

    def test_image_tag(self):
        app = App(
            'test',
            deployments={
                'images': {
                    'template': 'image-template-{tag}'
                }
            }
        )
        self.assertEqual(app.make_image({'image-tag': 'I0'}), 'image-template-I0')

    def test_image_tag_from_yaml(self):
        path = create_test_yaml()
        app = App('test', path)
        self.assertEqual(app.values['image'], 'template-tag-myimagetag')

    def test_images_key_deleted(self):
        path = create_test_yaml()
        app = App('test', path)
        self.assertNotIn('images', app.values)
