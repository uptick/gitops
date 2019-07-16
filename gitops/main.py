from invoke import Program, Collection
from .core import summary, bump


namespace = Collection()
# namespace.add_collection(core)
namespace.add_task(summary)
namespace.add_task(bump)

program = Program(namespace=namespace, version='0.1.0')
