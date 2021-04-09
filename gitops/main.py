from invoke import Collection, Program, Task

import pkg_resources

from . import core, db, shorthands

version = pkg_resources.require("gitops")[0].version

namespace = Collection()

# Load up some of our functions into the root namespace.
for core_ns in [core, shorthands]:
    tasks = filter(
        lambda x: isinstance(x, Task),
        vars(core_ns).values()
    )
    for task in tasks:
        namespace.add_task(task)

# Namespace the rarer ones.
namespace.add_collection(db)

program = Program(namespace=namespace, version=version)
