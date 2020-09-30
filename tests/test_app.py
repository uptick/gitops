from unittest import TestCase

from common.app import App, Chart

from .utils import create_test_yaml


class MakeImageTests(TestCase):
    def test_direct_image(self):
        app = App('test', deployments={'image': 'I0', 'chart': 'https://github.com/uptick/workforce'})
        self.assertEqual(app.values['image'], 'I0')

    def test_image_tag(self):
        app = App(
            'test',
            deployments={
                'images': {
                    'template': 'image-template-{tag}'
                },
                'chart': 'https://uptick.com/uptick/workforce',
                'image-tag': 'I0'
            }
        )
        self.assertEqual(app.values['image'], 'image-template-I0')

    def test_no_image_tag_is_valid(self):
        app = App(
            'test',
            deployments={
                'chart': 'https://uptick.com/uptick/workforce',
            }
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


class TestChart(TestCase):
    def test_string_git_chart_is_parsed_properly_as_git(self):
        chart = Chart('https://github.com/uptick/workforce')

        self.assertEqual(chart.type, 'git')
        self.assertEqual(chart.git_repo_url, 'https://github.com/uptick/workforce')
        self.assertIsNone(chart.git_sha)

    def test_git_repo_url_sha_is_parsed_properly(self):
        chart = Chart('https://github.com/uptick/workforce@123')

        self.assertEqual(chart.type, 'git')
        self.assertEqual(chart.git_repo_url, 'https://github.com/uptick/workforce')
        self.assertEqual(chart.git_sha, '123')

    def test_git_repo_config_is_parsed_properly(self):
        chart = Chart({
            'type': 'git',
            'git_repo_url': 'https://github.com/uptick/workforce@123'
        })

        self.assertEqual(chart.type, 'git')
        self.assertEqual(chart.git_repo_url, 'https://github.com/uptick/workforce')
        self.assertEqual(chart.git_sha, '123')

    def test_helm_repo_is_parsed_properly(self):
        chart = Chart({
            'type': 'helm',
            'helm_repo': 'brigade',
            'helm_repo_url': 'https://brigade',
            'helm_chart': 'brigade/brigade',
        })

        self.assertEqual(chart.type, 'helm')
        self.assertEqual(chart.helm_repo_url, 'https://brigade')
        self.assertEqual(chart.helm_chart, 'brigade/brigade')

    def test_local_repo_is_parsed_properly(self):
        chart = Chart({
            'type': 'local',
            'path': '.',
        })

        self.assertEqual(chart.type, 'local')
        self.assertEqual(chart.path, '.')
