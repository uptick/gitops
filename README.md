# GitOps

Continuous delivery for your cluster.

## Overview

Using CI/CD for applications is a wonderful technique to ease the pain of
DevOps, wouldn't it be nice to apply the same workflow to cluster provisioning?

GitOps integrates a multi-tenanted cluster with a GitHub repository. Changes
made to the repository are sent to GitOps running on the cluster, which then
provisions the calculated changes.

Currently Kubernetes/Helm is the only supported cluster interface. All changes
to the cluster are performed as applications of Helm charts.

## Installation

Secrets are encrypted with git-crypt in `.envrc`. Contact someone who has access to have your gpg key added.

Gitops has a helm chart defining its deployment. Invoke scripts are provided to make deployment painless. See `tasks.py`.

## Roadmap

 * Handle failure on initial application deployment.
 * Better error reporting on failures.
 * Forced redeployment interface.
 * Make kubernetes specific code modular so that we can start to support multiple deployment methods.
 * Secrets removed from .envrc in the repo. Maybe change chart? Instead we'll provide a setup script to generate an ignored secrets file. Ensure secrets are not present in repo history. This allows us to move to open source.
 * Invoke commands and other tools should be extracted from the uptick-cluster repo, added here and packaged up. Package should create /usr/bin/gitops to act as a CLI interface. Convert invoke commands to this new interface.
 * Add a command to create a template cluster repo (ala uptick-cluster) and give instructions to push it up and set up a webhook.

Developer experience should look something like:
```
pip install gitops
gitops create-repository
    -> Creates cluster repo (maybe with examples?)
    -> Explains or pushes repo up somewhere.
    -> Explains or sets up a webhook on that repo.
gitops create-secrets
    -> Either downloads secrets from AWS using awscli or
    -> Prompts for each secret individually.
gitops deploy-server
    -> helm upgrade gitops chart... (see tasks.py:deploy)
# Use as normal anywhere you want (like uptick-cluster invoke scripts)
gitops summary
gitops bump```