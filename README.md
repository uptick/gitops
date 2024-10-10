# Gitops

[![PyPI version](https://badge.fury.io/py/gitops.svg)](https://pypi.org/project/gitops/)
[![versions](https://img.shields.io/pypi/pyversions/gitops.svg)](https://pypi.org/project/gitops/)
[![Test](https://github.com/uptick/gitops/workflows/Test/badge.svg)](https://github.com/uptick/gitops/actions?query=workflow%3ATest)
[![Lint](https://github.com/uptick/gitops/workflows/Lint/badge.svg)](https://github.com/uptick/gitops/actions?query=workflow%3ALint)

Manage multiple apps across one or more k8s clusters.

## Overview

Keeping track of numerous of single-tenanted application deployments can quickly become a handful. Enter Gitops!

The tool has two halves:

- Gitops Server - an instance of this gets deployed to each of your kubernetes clusters, listening on changes made to your gitops cluster repo. The server's responsibility is to update the deployments on the cluster it lives on to match the app specifications in the repo.
- Gitops CLI - this is a tool that you can use to interact comfortably with your cluster repo. It allows listing all deployed applications, what images they're presently running on, and which clusters they live on. It also provides numerous operations that can be applied to one or more apps at a time, such as bumping to a newer version of an image, or running a particular command across your app cohort.

You can install the CLI tool with: `pip install gitops`

Currently Kubernetes/Helm is the only supported cluster interface. All app deployments are performed as applications of Helm charts.

## So what's a "cluster repo"?

This is a git repository that you set up, where you list out all of your applications and how you want them deployed. It looks like this:

<pre>
.
+- apps
   +- app_0
      +- deployment.yml
      +- secrets.yml
   +- app_1
      +- deployment.yml
      +- secrets.yml
+- jobs
</pre>

## Installation

Secrets should be placed in `secrets.env`. The example file `secrets.example.env` has the environment variables you will need to supply.

Add `export GITOPS_APPS_DIRECTORY=~/<cluster-apps-folder>` to invoke gitops from any directory.

Ensure that gitops has `edit` access to the namespace it is deploying to. An example RoleBinding is:

```
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: gitops-role-binding
  namespace: workforce
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: edit
subjects:
- kind: ServiceAccount
  name: default
  namespace: gitops
```

## Contribution
We're using [releaseplease](https://github.com/googleapis/release-please), to publish a new version do the following:
1. Checkout a feature branch and make the changes
   1. Make sure to follow instructions for writing commits by [releaseplease](https://github.com/googleapis/release-please)
      1. fix: which represents bug fixes, and correlates to a SemVer patch.
      2. feat: which represents a new feature, and correlates to a SemVer minor.
      3. feat!:, or fix!:, refactor!:, etc., which represent a breaking change (indicated by the !) and will result in a SemVer major.
2. Push changes and get the PR approved
3. Once it is merged; an additional PR containing the release changes needs to be merged to create a release.
