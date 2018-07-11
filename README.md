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

TODO: Setup the repository.

TODO: Install GitOps. Include details on domain name?

TODO: Kubernetes cluster and Helm.

TODO: Secrets (kubectl, GitHub, etc).

## Repository structure

TODO

## Roadmap

 * Handle failure on initial application deployment.

 * Better error reporting on failures.
 
 * Forced redeployment interface.

## Contributing

TODO
