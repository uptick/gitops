from invoke import run, task


@task
def build(ctx):
    """ Build and push a Docker image to ECR.

    Uses the short hash code for the Git repo to identify this build. This allows
    for easier rollback.
    """
    tag = run('git rev-parse --short HEAD', hide=True).stdout.strip()
    tag = 'latest'
    local = f'uptick/gitops:{tag}'
    print(f'Building container ({local}) ... ', end='', flush=True)
    run(f'docker build -t {local} .', hide=True)
    print('ok')
    print(f'Pushing to ECR ... ', flush=True)
    login = run('aws ecr get-login --no-include-email', hide=True, warn=False).stdout.strip()
    run(login, hide=True)
    remote = f'305686791668.dkr.ecr.ap-southeast-2.amazonaws.com/gitops:{tag}'
    run(f'docker tag {local} {remote}', hide=True)
    run(f'docker push {remote}', pty=True)
