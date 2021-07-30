import os

CLUSTER_NAME = os.getenv("CLUSTER_NAME", "")
# Namespace to search/deploy into
CLUSTER_NAMESPACE = os.getenv("CLUSTER_NAMESPACE", "")
ACCOUNT_ID = os.getenv("ACCOUNT_ID", "")
GITHUB_WEBHOOK_KEY = os.getenv("GITHUB_WEBHOOK_KEY", "")
