from invoke import Program, Collection, Task
from . import core, shorthands, db, newtenant, script


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
namespace.add_collection(newtenant)
namespace.add_collection(script)

program = Program(namespace=namespace, version='0.1.0')
