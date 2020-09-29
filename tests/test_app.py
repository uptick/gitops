from unittest import TestCase

from common.app import App

from .utils import create_test_yaml


class MakeImageTests(TestCase):
    def test_direct_image(self):
        app = App('test', deployments={'image': 'I0'})
        self.assertEqual(app.values['image'], 'I0')

    def test_image_tag(self):
        app = App(
            'test',
            deployments={
                'images': {
                    'template': 'image-template-{tag}'
                },
                'image-tag': 'I0'
            }
        )
        self.assertEqual(app.values['image'], 'image-template-I0')

    def test_no_image_tag_is_valid(self):
        app = App(
            'test',
        )
        self.assertIsNone(app.values.get('image'))

    def test_image_tag_from_yaml(self):
        path = create_test_yaml()
        app = App('test', path)
        self.assertEqual(app.values['image'], 'template-tag-myimagetag')

    def test_images_key_deleted(self):
        path = create_test_yaml()
        app = App('test', path)
        self.assertNotIn('images', app.values)
