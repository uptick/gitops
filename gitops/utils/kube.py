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
from invoke import run, task
from invoke.exceptions import UnexpectedExit

import boto3
import humanize
from colorama import Fore
from gitops_server.namespace import Namespace

from gitops.utils.async_runner import async_run

from .exceptions import CommandError


async def run_job(app, command, cleanup=True, sequential=True):
    job_id = make_key(4).lower()
    app_name = app['name']
    values = {
        'name': f'{app_name}-command-{job_id}',
        'app': app_name,
        'command': str(shlex.split(command)),
        'image': app['image'],
    }
    return await _run_job('jobs/command-job.yml', values, 'workforce', attach=True, cleanup=cleanup, sequential=sequential)


def build_image(local_image, path=None, tag=None):
    """ Build a Docker image.

    :param local_image: Image to write as.
    :param path: Run command from this path.
    :param tag: Tag to use for image.
    """
    local_image = get_image(local_image, tag)
    intro = f'Building container {Fore.BLUE}{local_image}{Fore.RESET} ... '
    with run_wrapper(intro):
        cmd = f'docker build -t {local_image} .'
        if path:
            cmd = f'cd {path} && {cmd}'
        run(cmd, hide=True)


def tag_image(local_image, remote_image, tag=None):
    """ Tag Docker image.

    Used to tag a local image to match AWS image signature prior to a push.

    :param local_image: Image to tag.
    :param remote_image: Image to tag as.
    :param tag: Tag to use for image.
    """
    local_image = get_image(local_image, tag)
    remote_image = get_image(remote_image, tag)
    intro = (
        f'Tagging container {Fore.BLUE}{local_image}{Fore.RESET}'
        f' as {Fore.BLUE}{local_image}{Fore.RESET} ... '
    )
    with run_wrapper(intro):
        run(f'docker tag {remote_image} {local_image}')


def build_bundle(bucket, path=None):
    """ Build a JS bundle.

    Uses `yarn` to build a JS bundle. Accepts a bucket parameter to pass into
    the build to set the public prefix. This is useful for production builds to
    specify the S3 bucket to use.

    :param bucket: Prefix to use in the build.
    """
    intro = f'Building bundle for bucket {Fore.BLUE}{bucket}{Fore.RESET} ... '
    with run_wrapper(intro):
        cmd = f'yarn && yarn build:prod --env.bucket={bucket}'
        if path:
            cmd = f'cd {path} && {cmd}'
        run(cmd, hide=True)


def push_image(local_image, remote_image, path=None, tag=None):
    """ Push image to AWS.

    :param local_image: Image to push.
    :param remote_image: Image to tag as.
    :param tag: Tag to use for image.
    """
    tag = get_tag(tag)
    remote_image = get_image(remote_image, tag)
    intro = (
        f'Pushing {Fore.BLUE}{local_image}{Fore.RESET} to ECR'
        f' {Fore.BLUE}{remote_image}{Fore.RESET} ... '
    )
    with run_wrapper(intro):
        login = run(
            'aws ecr get-login --no-include-email',
            hide=True,
            warn=False
        ).stdout.strip()
        run(login, hide=True)
        run(f'docker tag {local_image} {remote_image}', hide=True)
        run(f'docker push {remote_image}', hide=True)


def list_backups(product, prefix):
    """ List application backups.
    """
    backups = get_backups(product, prefix)
    for ii, backup in enumerate(reversed(backups)):
        index = len(backups) - ii
        size = humanize.naturalsize(backup[2])
        msg = (
            f'{Fore.BLUE}{index:4}{Fore.RESET}. {backup[1]}'
            f' - {Fore.GREEN}{size}{Fore.RESET}'
        )
        print(msg)


def download_backup(product, prefix, index, path=None, datestamp=False):
    s3 = get_client('s3')
    key = get_backups(product, prefix)[int(index) - 1][3]
    url = s3.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': 'uptick-backups',
            'Key': key
        }
    )
    name = prefix
    if datestamp:
        name += f'-{get_backup_datestamp(url)}'
    name += '.dump'
    if path:
        name = os.path.join(path, name)
    print(f'Downloading to {Fore.BLUE}{name}{Fore.RESET} ... ', end='', flush=True)
    run(f'curl "{url}" -s | zcat > {name}')
    print(f'{Fore.GREEN}ok{Fore.RESET}')


@task
def copy_db(ctx, source, destination):
    """ Copy database between two applications.
    """
    with tempfile.NamedTemporaryFile('wt', suffix='.yml') as tmp:
        job = open('copy-db-job.yml', 'r').read()
        job = job.replace('{{ source }}', source)
        job = job.replace('{{ destination }}', destination)
        tmp.write(job)
        tmp.flush()
        run(f'kubectl create -n workforce -f {tmp.name}', hide=True)
        print('Waiting for copy to complete ... ', end='', flush=True)
        run((
            'kubectl wait'
            ' -n workforce'
            ' --for=condition=complete'
            ' --timeout=-1s'
            ' job/copy-db-{source}-{destination}'
        ).format(
            source=source,
            destination=destination
        ), hide=True)
        print('done')
        run((
            'kubectl delete -n workforce job'
            ' copy-db-{source}-{destination}'
        ).format(
            source=source,
            destination=destination
        ), hide=True)


@task
def create_backup_secrets(ctx, namespace='workforce'):
    """ Create backup job secrets.

    Before running backups certain secret keys need to be available to
    the job. This creates the secrets on the cluster.
    """
    run((
        'kubectl create secret generic backups-secrets'
        f' -n {namespace}'
        ' --from-literal=AWS_ACCESS_KEY_ID={}'
        ' --from-literal=AWS_SECRET_ACCESS_KEY={}'
    ).format(
        get_secret('BACKUPS_AWS_ACCESS_KEY_ID'),
        get_secret('BACKUPS_AWS_SECRET_ACCESS_KEY')
    ))


def get_backups(product, prefix):
    s3 = boto3.resource('s3')
    bucket = s3.Bucket('uptick-backups')
    all_backups = []
    for obj in bucket.objects.filter(Prefix=f'{product}/{prefix}/'):
        name = obj.key.split('/')[-1].split('.')[0]
        if not name:
            continue
        dt = datetime.strptime(name, '%Y-%m-%d_%H-%M-%S')
        all_backups.append((name, dt, obj.size, obj.key))
    return sorted(all_backups, key=lambda x: x[1])


def get_backup_datestamp(url):
    jj = url.find('?')
    ii = url.rfind('/', 0, jj) + 1
    return url[ii:jj][:-4]


def get_tag(tag=None):
    if tag:
        return tag
    return run('git rev-parse --short HEAD', hide=True).stdout.strip()


def get_image(image, tag=None):
    tag = get_tag(tag)
    if tag:
        image = image + f':{tag}'
    return image


def get_secret(name, base64=False):
    try:
        value = os.environ[name]
    except KeyError:
        msg = (
            f'Variable {Fore.RED}{name}{Fore.RESET} missing from environment.'
        )
        raise CommandError(msg)
    if base64:
        value = b64encode(value.encode()).decode()
    else:
        value = shlex.quote(value)
    return value


def get_secret_file(name):
    data = open(os.environ[name], 'rb').read()
    return b64encode(data).decode()


def get_app_image(app):
    ns = Namespace(app)
    ns.from_path(f'../apps/{app}')
    return ns.values['image']


def get_session():
    return boto3.Session(
        aws_access_key_id=os.environ['BACKUPS_AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['BACKUPS_AWS_SECRET_ACCESS_KEY']
    )


def get_client(name):
    session = get_session()
    return session.client(name)


@contextmanager
def run_wrapper(intro):
    print(intro, end='', flush=True)
    try:
        yield
    except CommandError as e:
        print(f'{Fore.RED}error{Fore.RESET}')
        print(f' \u2514 {e}')
        sys.exit(1)
    except UnexpectedExit as e:
        print(f'{Fore.RED}error{Fore.RESET}')
        print(e)
        sys.exit(1)
    else:
        print(f'{Fore.GREEN}ok{Fore.RESET}')


def make_key(length=64):
    """ Generate a sequence of random characters.
    """
    return ''.join(
        random.SystemRandom().choice(
            string.ascii_uppercase + string.digits
        ) for _ in range(length)
    )


async def _run_job(path, values={}, namespace='default', attach=False, cleanup=True, sequential=True):
    name = values['name']
    logs = ''
    with tempfile.NamedTemporaryFile('wt', suffix='.yml') as tmp:
        resource = open(path, 'r').read()
        for k, v in values.items():
            resource = resource.replace('{{ %s }}' % k, v)
        tmp.write(resource)
        tmp.flush()
        await async_run(f'kubectl create -n {namespace} -f {tmp.name}')
        cmd = (
            'kubectl get pods'
            ' -n {namespace}'
            ' --selector=job-name={name}'
            ' -o jsonpath=\'{{.items[*].metadata.name}}\''
        ).format(
            name=name,
            namespace=namespace
        )
        @retry
        async def _find_pod():
            stdout, _, _ = await async_run(cmd)
            pod = stdout.decode()
            if not pod:
                raise CommandError('Failed to find pod.')
            return pod
        pod = await _find_pod()
        try:
            if not attach:
                intro = 'Waiting for job to complete ... '
                with run_wrapper(intro):
                    cmd = (
                        'kubectl wait'
                        f' -n {namespace}'
                        ' --for=condition=complete'
                        ' --timeout=-1s'
                        f' job/{name}'
                    )
                    _, _, output_log = await async_run(cmd)
                    logs += output_log
            else:
                await wait_for_pod(namespace, pod)
                cmd = (
                    'kubectl attach'
                    f' -n {namespace}'
                    ' -it'
                    f' {pod}'
                )
                try:
                    if sequential:
                        # If we're not running asynchronously, use invoke.run to preserve interactivity for shell_plus, etc.
                        run(cmd, pty=True)
                    else:
                        _, _, output_log = await async_run(cmd)
                        logs += output_log

                except Exception as e:
                    if 'current phase is Succeeded' not in str(e.result.stdout):
                        raise e
        except Exception as e:
            if 'current phase is Succeeded' not in str(e.result.stdout):
                raise e
        finally:
            if cleanup:
                cmd = f'kubectl delete -n {namespace} job {name}'
                await async_run(cmd)
    return logs


async def wait_for_pod(namespace, pod):
    while True:
        cmd = (
            'kubectl get pod'
            f' -n {namespace}'
            ' -o jsonpath="{.status.phase}"'
            f' {pod}'
        )
        stdout, _, _ = await async_run(cmd)
        stdout = stdout.decode().lower()
        if stdout != 'pending':
            return stdout


def get_pod_names(namespace, selector):
    cmd = (
        'kubectl get pods'
        f' -n {namespace}'
        f' --selector={selector}'
        ' -o jsonpath=\'{{.items[*].metadata.name}}\''
    ).format(
        namespace=namespace,
        selector=selector
    )
    return run(cmd, hide=True).stdout.strip().split()


def get_pod_logs(namespace, pod):
    cmd = (
        'kubectl logs'
        f' -n {namespace}'
        f' {pod}'
    )
    result = run(cmd, hide=True)
    return result.stdout


def retry(*args, max_attempts=3, delay=1):
    """ A decorator for retrying a function.

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
    print(textwrap.fill(
        f'This operation will {Fore.RED}destroy{Fore.RESET}'
        f' the data currently stored in {Fore.RED}{database}{Fore.RESET}.'
        ' Please confirm by typing the name of the database'
        f' ({Fore.BLUE}{database}{Fore.RESET}):'
    ))
    value = input('> ')
    if value != database:
        print('Does not match, aborting.')
        sys.exit(1)
