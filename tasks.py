import json
import os
from base64 import b64encode

import yaml
from invoke import run, task


@task
def test(ctx, pty=True):
    run("py.test")


@task
def lint(ctx, pty=True):
    run("pre-commit run --all-files")


@task
def build(ctx):
    """Build and push a Docker image to ECR.

    Uses the short hash code for the Git repo to identify this build. This
    allows for easier rollback.
    """
    local = get_latest_image()
    print(f"Building container ({local}) ... ", flush=True)
    run(f"docker build -t {local} .")


@task
def push(ctx, tag=None):
    local = get_latest_image()
    remote = get_remote_image(tag)
    password = run("aws ecr get-login-password", hide=True, warn=False).stdout.strip()
    run(f"docker login -u AWS -p {password} https://{get_repo_uri()}", hide=True)
    run(f"docker tag {local} {remote}", hide=False)
    print(f"Pushing to ECR ({remote}) ... ", flush=True)
    run(f"docker push {remote}", pty=True)


@task
def logs(ctx):
    name = run(
        "kubectl -n default get pods --selector=app=gitops -o jsonpath='{.items[*].metadata.name}'",
        hide=True,
    ).stdout.strip()
    run(f"kubectl -n default logs -f {name}", pty=True)


@task
def test_helm(ctx):
    """Tests / validates a dry installation of the helm chart"""
    run(
        "helm install --dry-run --debug --set environment.GIT_CRYPT_KEY_FILE='test' --set"
        " environment.CLUSTER_NAME='hi' --set environment.CLUSTER_NAMESPACE='test' debug"
        " charts/gitops/"
    )


def get_commit_tag():
    return run("git rev-parse --short HEAD", hide=True).stdout.strip()


def get_account_id():
    caller_identity = run("aws sts get-caller-identity", hide=True).stdout.strip()
    return json.loads(caller_identity)["Account"]


def get_repo_uri():
    return f"{get_account_id()}.dkr.ecr.ap-southeast-2.amazonaws.com"


def get_latest_image() -> str:
    return get_remote_image(tag="latest")


def get_remote_image(tag=None) -> str:
    tag = tag or get_commit_tag()
    return f"{get_repo_uri()}/gitops:{tag}"


def get_secret(name):
    return b64encode(os.environ[name].encode()).decode()


def get_secret_file(name):
    data = open(os.environ[name], "rb").read()
    return b64encode(data).decode()


def get_cluster_name():
    data = run("kubectl config view", hide=True).stdout.strip()
    conf = yaml.safe_load(data)
    contexts = {c["name"]: c["context"] for c in conf["contexts"]}
    return contexts[conf["current-context"]]["cluster"].split(":cluster/")[-1]
