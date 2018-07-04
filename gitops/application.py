import os

from .utils import run


class Application:
    def __init__(self, namespace, path):
        self.namespace = namespace
        self.from_path(path)

    def from_path(self, path):
        self.path = path
        parts = path.split('/')
        self.name = parts[-1]

    def deploy(self):
        return run((
            'REVISION={revision} kubernetes-deploy {namespace}'
            ' {context} --template-dir={path}'
            ' --bindings="image={image}"'
        ).format(
            revision=self.namespace.cluster.revision,
            namespace=self.namespace.name,
            context=os.environ['KUBE_CONTEXT'],
            path=self.path,
            image=self.namespace.images[self.name]
        ))
