# GitOps Server

## Deploying

Ensure you:
- Are in the root directory of gitops.
- Have assumed an aws identity/role that's in the AWS account you wish to deploy gitops to.
- Have your current kube config context pointing at the cluster you wish to deploy gitops on.
- Have set up a webhook in github for your app definitions repo to post change updates to https://gitops.<cluster_env>.onuptick.com/webhook

Run:

    inv redeploy

Cool. That's it.
