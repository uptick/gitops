import os

CLUSTER_NAME = os.getenv('CLUSTER_NAME', "")
ACCOUNT_ID = os.getenv('ACCOUNT_ID', "")
# os.environ['GITHUB_WEBHOOK_KEY'].encode()

# url_with_oauth_token = git_repo_url.replace("://", f"://{os.environ['GITHUB_OAUTH_TOKEN'].strip()}@")

# await run(f'git clone {url_with_oauth_token} {path}; cd {path}; git checkout {sha}')

# await run(f'cd {path}; git-crypt unlock {os.environ["GIT_CRYPT_KEY_FILE"]}')
