import os
import yaml
from base64 import b64encode
from invoke import run, task

from dotenv import load_dotenv

ENV = 'develop'  # TODO: Read this in from somewhere (current branch, or cluster name)
REPO_URI = '964754172176.dkr.ecr.ap-southeast-2.amazonaws.com'


@task
def test(ctx, pty=True):
    run('docker-compose run --service-ports --rm web python -m unittest -v')


@task
def redeploy(ctx, kubeconfig=''):
    build(ctx)
    push(ctx)
    deploy(ctx, kubeconfig=kubeconfig)


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
    run(f'docker login -u AWS -p {password} https://{REPO_URI}', hide=True)
    run(f'docker tag {local} {remote}', hide=True)
    run(f'docker push {remote}', pty=True)


@task
def deploy(ctx, kubeconfig=''):
    load_dotenv('secrets.env')
    cluster_details = get_cluster_details(kubeconfig or os.environ['KUBE_CONFIG_FILE'])
    run((
        'helm upgrade'
        ' gitops'
        ' chart'
        ' --install'
        ' --wait'
        ' --namespace default'
        f' --set image={get_remote_image()}'
        f' --set domain={ENV}.onuptick.com'
        ' --set environment.GIT_CRYPT_KEY_FILE=/etc/gitops/git_crypt_key'
        f" --set environment.CLUSTER_NAME={cluster_details['name']}"
        f" --set secrets.SLACK_URL={get_secret('SLACK_URL')}"
        f" --set secrets.GITHUB_OAUTH_TOKEN={get_secret('GITHUB_OAUTH_TOKEN')}"
        f" --set secrets.GITHUB_WEBHOOK_KEY={get_secret('GITHUB_WEBHOOK_KEY')}"
        f" --set secrets.GIT_CRYPT_KEY={get_secret_file('GIT_CRYPT_KEY_FILE')}"
        f" --set secrets.KUBE_CONFIG={cluster_details['kube_config']}"
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


def get_local_image():
    return f'uptick/gitops:{get_tag()}'


def get_remote_image():
    return f'{REPO_URI}/{ENV}/gitops:{get_tag()}'


def get_secret(name):
    return b64encode(os.environ[name].encode()).decode()


def get_secret_file(name):
    data = open(os.environ[name], 'rb').read()
    return b64encode(data).decode()


def get_cluster_details(filename):
    with open(filename, 'rb') as f:
        data = f.read()
        conf = yaml.load(data)
        contexts = {c['name']: c['context'] for c in conf['contexts']}
        return {
            'kube_config': b64encode(data).decode(),
            'name': contexts[conf['current-context']]['cluster'].split(':cluster/')[-1],
        }
