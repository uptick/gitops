# GitOps

Continuous delivery for your cluster.

## Overview

Using CI/CD for applications is a wonderful technique to ease the pain of DevOps,wouldn't it be nice to apply the same workflow to cluster provisioning?

GitOps is a two-part system. A library of commands is used to manage a
single-tenanted cluster within a git repository, and the server component watches
the repository and provisions the calculated changes.

Currently Kubernetes/Helm is the only supported cluster interface. All changes
to the cluster are performed as applications of Helm charts.

## Installation

Secrets should be placed in `secrets.env`. The example file `secrets.example.env` has the environment variables you will need to supply.

Gitops has a helm chart defining its deployment. Invoke scripts are provided to make deployment painless. See `tasks.py`.

## Roadmap

 * Handle failure on initial application deployment.
 * Better error reporting on failures.
 * Forced redeployment interface.
 * Make kubernetes specific code modular so that we can start to support multiple deployment methods.
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