import asyncio
import inspect
import os
import random
import shlex
import string
import sys
import tempfile
import textwrap
import time
from base64 import b64encode
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from typing import Dict, TypedDict

import boto3
import humanize
import yaml
from colorama import Fore
from invoke import run
from invoke.exceptions import UnexpectedExit

from gitops.common.app import App
from gitops.settings import get_apps_directory
from gitops.utils.async_runner import async_run

from .exceptions import CommandError


class ResourceSpec(TypedDict):
    memory: str
    cpu: str


class ContainerResources(TypedDict):
    limits: ResourceSpec
    requests: ResourceSpec


async def run_job(
    app: App,
    command,
    cleanup=True,
    sequential=True,
    cpu: int = None,
    memory: int = None,
):
    job_id = make_key(4).lower()
    values = {
        "name": f"{app.name}-command-{job_id}",
        "app": app.name,
        "command": str(shlex.split(command)),
        "image": app.image,
        "serviceAccountName": app.service_account_name,
    }
    extra_labels = {}
    container_resources = {}

    if cpu and memory:
        cpu_request = f"{cpu}m" if cpu else ""
        memory_request = f"{memory}Mi" if memory else ""
        container_resources = ContainerResources(
            limits=ResourceSpec(cpu=cpu_request, memory=memory_request),
            requests=ResourceSpec(cpu=cpu_request, memory=memory_request),
        )

    return await _run_job(
        "jobs/command-job.yml",
        values,
        context=app.cluster,
        namespace=app.namespace,
        attach=True,
        cleanup=cleanup,
        sequential=sequential,
        extra_labels=extra_labels,
        container_resources=container_resources,
    )


def list_backups(product, prefix):
    """List application backups."""
    backups = get_backups(product, prefix)
    for ii, backup in enumerate(reversed(backups)):
        index = len(backups) - ii
        size = humanize.naturalsize(backup[2])
        print(f"{Fore.BLUE}{index:4}{Fore.RESET}. {backup[1]} - {Fore.GREEN}{size}{Fore.RESET}")


def download_backup(product, prefix, index, path=None, datestamp=False):
    s3 = boto3.client("s3")
    key = get_backups(product, prefix)[int(index) - 1][3]
    url = s3.generate_presigned_url("get_object", Params={"Bucket": "uptick-backups", "Key": key})
    name = prefix
    if datestamp:
        name += f"-{get_backup_datestamp(url)}"
    name += ".dump"
    if path:
        name = os.path.join(path, name)
    print(f"Downloading to {Fore.BLUE}{name}{Fore.RESET} ... ", end="", flush=True)
    run(f'curl "{url}" -s | zcat > {name}')
    print(f"{Fore.GREEN}ok{Fore.RESET}")


def copy_db(ctx, source, destination, context=""):
    """Copy database between two applications."""
    with tempfile.NamedTemporaryFile("wt", suffix=".yml") as tmp:
        job = open("copy-db-job.yml", "r").read()
        job = job.replace("{{ source }}", source)
        job = job.replace("{{ destination }}", destination)
        tmp.write(job)
        tmp.flush()
        run(f"kubectl create -n workforce -f {tmp.name}", hide=True)
        print("Waiting for copy to complete ... ", end="", flush=True)
        run(
            (
                "kubectl wait"
                f" --context {context}"
                " -n workforce"
                " --for=condition=complete"
                " --timeout=-1s"
                " job/copy-db-{source}-{destination}"
            ).format(source=source, destination=destination),
            hide=True,
        )
        print("done")
        run(
            ("kubectl delete -n workforce job copy-db-{source}-{destination}").format(
                source=source, destination=destination
            ),
            hide=True,
        )


def get_backups(product, prefix):
    s3 = boto3.resource("s3")
    bucket = s3.Bucket("uptick-backups")
    all_backups = []
    for obj in bucket.objects.filter(Prefix=f"{product}/{prefix}/"):
        name = obj.key.split("/")[-1].split(".")[0]
        if not name:
            continue
        dt = datetime.strptime(name, "%Y-%m-%d_%H-%M-%S")
        all_backups.append((name, dt, obj.size, obj.key))
    return sorted(all_backups, key=lambda x: x[1])


def get_backup_datestamp(url):
    jj = url.find("?")
    ii = url.rfind("/", 0, jj) + 1
    return url[ii:jj][:-4]


def get_secret(name, base64=False):
    try:
        value = os.environ[name]
    except KeyError:
        msg = f"Variable {Fore.RED}{name}{Fore.RESET} missing from environment."
        raise CommandError(msg)
    if base64:
        value = b64encode(value.encode()).decode()
    else:
        value = shlex.quote(value)
    return value


@contextmanager
def run_wrapper(intro):
    print(intro, end="", flush=True)
    try:
        yield
    except CommandError as e:
        print(f"{Fore.RED}error{Fore.RESET}")
        print(f" \u2514 {e}")
        sys.exit(1)
    except UnexpectedExit as e:
        print(f"{Fore.RED}error{Fore.RESET}")
        print(e)
        sys.exit(1)
    else:
        print(f"{Fore.GREEN}ok{Fore.RESET}")


def make_key(length=64):
    """Generate a sequence of random characters."""
    return "".join(
        random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(length)
    )


def render_template(
    template: str,
    values: Dict = None,
    extra_labels: Dict = None,
    container_resources: ContainerResources = None,
) -> str:
    """Given a yaml of a K8s Job, replace template values and add extra labels to the pod spec"""
    extra_labels = extra_labels or {}
    values = values or {}

    # Replace keys using our templating language
    for k, v in values.items():
        template = template.replace("{{ %s }}" % k, v)

    job_json = yaml.safe_load(template)
    # Adding extra labels to k8s job pod spec
    for k, v in extra_labels.items():
        job_json["spec"]["template"]["metadata"]["labels"][k] = v
    if container_resources:
        job_json["spec"]["template"]["spec"]["containers"][0]["resources"] = container_resources

    return yaml.dump(job_json)


async def _run_job(
    path,
    values: Dict = None,
    context="",
    namespace="default",
    attach=False,
    cleanup=True,
    sequential=True,
    extra_labels: Dict = None,
    container_resources: ContainerResources = None,
):
    name = values["name"]
    logs = ""
    with tempfile.NamedTemporaryFile("wt", suffix=".yml") as tmp:
        # Generate yaml template to render
        rendered_template = render_template(
            open(get_apps_directory() / ".." / path, "r").read(),
            values,
            extra_labels,
            container_resources=container_resources,
        )
        tmp.write(rendered_template)
        tmp.flush()
        await async_run(f"kubectl create --context {context} -n {namespace} -f {tmp.name}")
        cmd = (
            "kubectl get pods"
            f" --context {context}"
            f" -n {namespace}"
            f" --selector=job-name={name}"
            " -o jsonpath='{.items[*].metadata.name}'"
        )

        @retry
        async def _find_pod():
            stdout, _, _ = await async_run(cmd)
            pod = stdout.decode()
            if not pod:
                raise CommandError("Failed to find pod.")
            return pod

        pod = await _find_pod()
        try:
            if not attach:
                intro = "Waiting for job to complete ... "
                with run_wrapper(intro):
                    cmd = (
                        "kubectl wait"
                        f" --context {context}"
                        f" -n {namespace}"
                        " --for=condition=complete"
                        " --timeout=-1s"
                        f" job/{name}"
                    )
                    _, _, output_log = await async_run(cmd)
                    logs += output_log
            else:
                await wait_for_pod(context, namespace, pod)
                cmd = f"kubectl attach --context {context} -n {namespace} -it {pod}"
                try:
                    if sequential:
                        # If we're not running asynchronously, use invoke.run to preserve interactivity for shell_plus, etc.
                        run(cmd, pty=True)
                    else:
                        _, _, output_log = await async_run(cmd)
                        logs += output_log

                except Exception as e:
                    if "current phase is Succeeded" not in str(e.result.stdout):
                        raise e
        except Exception as e:
            if "current phase is Succeeded" not in str(e.result.stdout):
                raise e
        finally:
            if cleanup:
                cmd = f"kubectl delete --context {context} -n {namespace} job {name}"
                await async_run(cmd)
    return logs


async def wait_for_pod(context, namespace, pod):
    while True:
        cmd = (
            "kubectl get pod"
            f" --context {context}"
            f" -n {namespace}"
            ' -o jsonpath="{.status.phase}"'
            f" {pod}"
        )
        stdout, _, _ = await async_run(cmd)
        stdout = stdout.decode().lower()
        if stdout != "pending":
            return stdout


def retry(*args, max_attempts=3, delay=1):
    """A decorator for retrying a function.

    After `max_attempts` failed attempts the last thrown exception
    is re-thrown.

    :param max_attempts: Maximum number of attempts.
    """

    def outer(f):
        if inspect.iscoroutinefunction(f):

            @wraps(f)
            async def inner(*args, **kwargs):
                attempt = 0
                while True:
                    try:
                        return await f(*args, **kwargs)
                    except Exception:
                        attempt += 1
                        if attempt >= max_attempts:
                            raise
                        await asyncio.sleep(delay)

        else:

            @wraps(f)
            def inner(*args, **kwargs):
                attempt = 0
                while True:
                    try:
                        return f(*args, **kwargs)
                    except Exception:
                        attempt += 1
                        if attempt >= max_attempts:
                            raise
                        time.sleep(delay)

        return inner

    if len(args) == 1 and callable(args[0]):
        return outer(args[0])
    else:
        return outer


def confirm_database(database):
    print(
        textwrap.fill(
            f"This operation will {Fore.RED}destroy{Fore.RESET}"
            f" the data currently stored in {Fore.RED}{database}{Fore.RESET}."
            " Please confirm by typing the name of the database"
            f" ({Fore.BLUE}{database}{Fore.RESET}):"
        )
    )
    value = input("> ")
    if value != database:
        print("Does not match, aborting.")
        sys.exit(1)
