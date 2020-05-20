import json
import os
import yaml
from base64 import b64encode
from invoke import run, task

from dotenv import load_dotenv


@task
def test(ctx, pty=True):
    run('docker-compose run --service-ports --rm web python -m unittest -v')


@task
def redeploy(ctx):
    build(ctx)
    push(ctx)
    deploy(ctx)


@task
def build(ctx):
    """ Build and push a Docker image to ECR.

    Uses the short hash code for the Git repo to identify this build. This
    allows for easier rollback.
    """
    local = get_local_image()
    print(f'Building container ({local}) ... ', flush=True)
    run(f'docker build -t {local} .')


@task
def push(ctx):
    local = get_local_image()
    remote = get_remote_image()
    print(f'Pushing to ECR ({local}) ... ', flush=True)
    password = run('aws ecr get-login-password', hide=True, warn=False).stdout.strip()
    run(f'docker login -u AWS -p {password} https://{get_repo_uri()}', hide=True)
    run(f'docker tag {local} {remote}', hide=True)
    run(f'docker push {remote}', pty=True)


@task
def deploy(ctx):
    load_dotenv('secrets.env')
    cluster_name = get_cluster_name()
    cluster_env = cluster_name[4:]  # Drops the leading 'eks-'  # TODO: adjust this so that gitops doesn't depend on this heuristic.
    run((
        'helm upgrade'
        ' gitops'
        ' chart'
        ' --install'
        ' --wait'
        ' --namespace default'
        f' --set image={get_remote_image()}'
        f" --set domain={cluster_env}.onuptick.com"
        ' --set environment.GIT_CRYPT_KEY_FILE=/etc/gitops/git_crypt_key'
        f" --set environment.CLUSTER_NAME={cluster_name}"
        f" --set secrets.ACCOUNT_ID={b64encode(get_account_id().encode()).decode()}"
        f" --set secrets.SLACK_URL={get_secret('SLACK_URL')}"
        f" --set secrets.GITHUB_OAUTH_TOKEN={get_secret('GITHUB_OAUTH_TOKEN')}"
        f" --set secrets.GITHUB_WEBHOOK_KEY={get_secret('GITHUB_WEBHOOK_KEY')}"
        f" --set secrets.GIT_CRYPT_KEY={get_secret_file('GIT_CRYPT_KEY_FILE')}"
    ))


@task
def logs(ctx):
    name = run(
        'kubectl -n default get pods --selector=app=gitops'
        ' -o jsonpath=\'{.items[*].metadata.name}\'',
        hide=True
    ).stdout.strip()
    run(f'kubectl -n default logs -f {name}', pty=True)


def get_tag():
    return run('git rev-parse --short HEAD', hide=True).stdout.strip()


def get_account_id():
    caller_identity = run('aws sts get-caller-identity', hide=True).stdout.strip()
    return json.loads(caller_identity)['Account']


def get_repo_uri():
    return f'{get_account_id()}.dkr.ecr.ap-southeast-2.amazonaws.com'


def get_local_image():
    return f'uptick/gitops:{get_tag()}'


def get_remote_image():
    return f'{get_repo_uri()}/gitops:{get_tag()}'


def get_secret(name):
    return b64encode(os.environ[name].encode()).decode()


def get_secret_file(name):
    data = open(os.environ[name], 'rb').read()
    return b64encode(data).decode()


def get_cluster_name():
    data = run('kubectl config view', hide=True).stdout.strip()
    conf = yaml.safe_load(data)
    contexts = {c['name']: c['context'] for c in conf['contexts']}
    return contexts[conf['current-context']]['cluster'].split(':cluster/')[-1],
