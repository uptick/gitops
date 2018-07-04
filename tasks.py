import os
from base64 import b64encode

from invoke import run, task

IMAGE_URI = '305686791668.dkr.ecr.ap-southeast-2.amazonaws.com/gitops:{tag}'


@task
def build(ctx):
    """ Build and push a Docker image to ECR.

    Uses the short hash code for the Git repo to identify this build. This allows
    for easier rollback.
    """
    tag = get_tag()
    local = f'uptick/gitops:{tag}'
    print(f'Building container ({local}) ... ', flush=True)
    run(f'docker build -t {local} .')
    print(f'Pushing to ECR ... ', flush=True)
    login = run('aws ecr get-login --no-include-email', hide=True, warn=False).stdout.strip()
    run(login, hide=True)
    remote = IMAGE_URI.format(tag=tag)
    run(f'docker tag {local} {remote}', hide=True)
    run(f'docker push {remote}', pty=True)


@task
def deploy(ctx):
    run((
        'helm upgrade'
        ' gitops'
        ' chart'
        ' --install'
        ' --namespace default'
        ' --set image={}'
        ' --set domain=.onuptick.com'
        ' --set environment.GIT_CRYPT_KEY_FILE=/etc/gitops/git_crypt_key'
        ' --set secrets.SLACK_URL={}'
        ' --set secrets.GITHUB_WEBHOOK_KEY={}'
        ' --set secrets.GIT_CRYPT_KEY={}'
    ).format(
        IMAGE_URI.format(tag=get_tag()),
        get_secret('SLACK_URL'),
        get_secret('GITHUB_WEBHOOK_KEY'),
        get_secret_file('GIT_CRYPT_KEY_FILE')
    ))


def get_tag():
    return run('git rev-parse --short HEAD', hide=True).stdout.strip()


def get_secret(name):
    return b64encode(os.environ[name].encode()).decode()


def get_secret_file(name):
    data = open(os.environ[name], 'rb').read()
    return b64encode(data).decode()
