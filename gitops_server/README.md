# GitOps Server

## Deploying

Ensure you:
- Are in the root directory of gitops.
- Have assumed an aws identity/role that's in the AWS account you wish to deploy gitops to.
- Have your current kube config context pointing at the cluster you wish to deploy gitops on.
- Have set up a webhook in github for your app definitions repo to post change updates to https://gitops.<cluster_env>.onuptick.com/webhook

<img src="https://user-images.githubusercontent.com/5036488/82446074-49891700-9ae9-11ea-97bf-87a65b8f394a.png" width="250">

Run:

    inv redeploy

Cool. That's it.


