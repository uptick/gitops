from unittest import TestCase
from unittest.mock import patch

from gitops.namespace import Namespace


class MakeImageTests(TestCase):
    def test_direct_image(self):
        ns = Namespace()
        self.assertEqual(
            ns.make_image({'image': 'I0'}),
            'I0'
        )

    def test_image_tag(self):
        ns = Namespace(
            'test',
            {
                'images': {
                    'template': 'image-template-{tag}'
                }
            }
        )
        self.assertEqual(
            ns.make_image({'image-tag': 'I0'}),
            'image-template-I0'
        )

    def test_image_group(self):
        ns = Namespace(
            'test',
            {
                'images': {
                    'template': 'image-template-{tag}',
                    'groups': {
                        'release': {
                            'image-tag': 'I0'
                        }
                    }
                }
            }
        )
        self.assertEqual(
            ns.make_image({'image-group': 'release'}),
            'image-template-I0'
        )


class MakeValuesTests(TestCase):
    def test_all(self):
        ns = Namespace(
            'test',
            {
                'images': {
                    'template': 'image-template-{tag}',
                    'groups': {
                        'release': {
                            'image-tag': 'I0'
                        }
                    }
                },
                'deployments': {
                    'server0': {
                        'image-group': 'release'
                    },
                    'server1': {
                        'image': 'I1'
                    }
                }
            }
        )
        self.assertEqual(
            ns.values,
            {
                'server0': {
                    'image-group': 'release',
                    'image': 'image-template-I0'
                },
                'server1': {
                    'image': 'I1'
                }
            }
        )


class DeployTests(TestCase):
    @patch('gitops.namespace.run')
    def test_all(self, run_mock):
        ns = Namespace(
            'test',
            {
                'images': {
                    'template': 'image-template-{tag}',
                    'groups': {
                        'release': {
                            'image-tag': 'I0'
                        }
                    }
                },
                'deployments': {
                    'server0': {
                        'image-group': 'release',
                        'containers': {
                            'fg': {
                                'replicas': 2
                            },
                            'bg': {
                                'replicas': 1
                            }
                        }
                    },
                    'server1': {
                        'image': 'I1',
                        'containers': {
                            'fg': {
                                'replicas': 2
                            },
                            'bg': {
                                'replicas': 1
                            }
                        }
                    }
                }
            }
        )
        ns.deploy()
        self.assertEqual(run_mock.call_count, 2)
        self.assertRegex(
            run_mock.call_args_list[0][0][0],
            r'helm upgrade --install --name=server0 -f .+\.yml'
            r' --namespace=test'
        )
        self.assertRegex(
            run_mock.call_args_list[1][0][0],
            r'helm upgrade --install --name=server1 -f .+\.yml'
            r' --namespace=test'
        )
