# Sample data obtained from https://github.com/uptick/uptick-cluster/settings/hooks/292837673
import json

payload = json.loads(
    """
{
  "ref": "refs/heads/master",
  "before": "2a2afbf3a9d8dc3a055b07aa4459bc8f16f06546",
  "after": "1d5a9a823e1b9b90f1976b357d0f2913c9a46d10",
  "repository": {
    "id": 139318783,
    "node_id": "MDEwOlJlcG9zaXRvcnkxMzkzMTg3ODM=",
    "name": "uptick-cluster",
    "full_name": "uptick/uptick-cluster",
    "private": true,
    "owner": {
      "name": "uptick",
      "email": "hello@uptickhq.com",
      "login": "uptick",
      "id": 10147530,
      "node_id": "MDEyOk9yZ2FuaXphdGlvbjEwMTQ3NTMw",
      "avatar_url": "https://avatars.githubusercontent.com/u/10147530?v=4",
      "gravatar_id": "",
      "url": "https://api.github.com/users/uptick",
      "html_url": "https://github.com/uptick",
      "followers_url": "https://api.github.com/users/uptick/followers",
      "following_url": "https://api.github.com/users/uptick/following{/other_user}",
      "gists_url": "https://api.github.com/users/uptick/gists{/gist_id}",
      "starred_url": "https://api.github.com/users/uptick/starred{/owner}{/repo}",
      "subscriptions_url": "https://api.github.com/users/uptick/subscriptions",
      "organizations_url": "https://api.github.com/users/uptick/orgs",
      "repos_url": "https://api.github.com/users/uptick/repos",
      "events_url": "https://api.github.com/users/uptick/events{/privacy}",
      "received_events_url": "https://api.github.com/users/uptick/received_events",
      "type": "Organization",
      "site_admin": false
    },
    "html_url": "https://github.com/uptick/uptick-cluster",
    "description": "Uptick Kubernetes cluster configuration.",
    "fork": false,
    "url": "https://github.com/uptick/uptick-cluster",
    "forks_url": "https://api.github.com/repos/uptick/uptick-cluster/forks",
    "keys_url": "https://api.github.com/repos/uptick/uptick-cluster/keys{/key_id}",
    "collaborators_url": "https://api.github.com/repos/uptick/uptick-cluster/collaborators{/collaborator}",
    "teams_url": "https://api.github.com/repos/uptick/uptick-cluster/teams",
    "hooks_url": "https://api.github.com/repos/uptick/uptick-cluster/hooks",
    "issue_events_url": "https://api.github.com/repos/uptick/uptick-cluster/issues/events{/number}",
    "events_url": "https://api.github.com/repos/uptick/uptick-cluster/events",
    "assignees_url": "https://api.github.com/repos/uptick/uptick-cluster/assignees{/user}",
    "branches_url": "https://api.github.com/repos/uptick/uptick-cluster/branches{/branch}",
    "tags_url": "https://api.github.com/repos/uptick/uptick-cluster/tags",
    "blobs_url": "https://api.github.com/repos/uptick/uptick-cluster/git/blobs{/sha}",
    "git_tags_url": "https://api.github.com/repos/uptick/uptick-cluster/git/tags{/sha}",
    "git_refs_url": "https://api.github.com/repos/uptick/uptick-cluster/git/refs{/sha}",
    "trees_url": "https://api.github.com/repos/uptick/uptick-cluster/git/trees{/sha}",
    "statuses_url": "https://api.github.com/repos/uptick/uptick-cluster/statuses/{sha}",
    "languages_url": "https://api.github.com/repos/uptick/uptick-cluster/languages",
    "stargazers_url": "https://api.github.com/repos/uptick/uptick-cluster/stargazers",
    "contributors_url": "https://api.github.com/repos/uptick/uptick-cluster/contributors",
    "subscribers_url": "https://api.github.com/repos/uptick/uptick-cluster/subscribers",
    "subscription_url": "https://api.github.com/repos/uptick/uptick-cluster/subscription",
    "commits_url": "https://api.github.com/repos/uptick/uptick-cluster/commits{/sha}",
    "git_commits_url": "https://api.github.com/repos/uptick/uptick-cluster/git/commits{/sha}",
    "comments_url": "https://api.github.com/repos/uptick/uptick-cluster/comments{/number}",
    "issue_comment_url": "https://api.github.com/repos/uptick/uptick-cluster/issues/comments{/number}",
    "contents_url": "https://api.github.com/repos/uptick/uptick-cluster/contents/{+path}",
    "compare_url": "https://api.github.com/repos/uptick/uptick-cluster/compare/{base}...{head}",
    "merges_url": "https://api.github.com/repos/uptick/uptick-cluster/merges",
    "archive_url": "https://api.github.com/repos/uptick/uptick-cluster/{archive_format}{/ref}",
    "downloads_url": "https://api.github.com/repos/uptick/uptick-cluster/downloads",
    "issues_url": "https://api.github.com/repos/uptick/uptick-cluster/issues{/number}",
    "pulls_url": "https://api.github.com/repos/uptick/uptick-cluster/pulls{/number}",
    "milestones_url": "https://api.github.com/repos/uptick/uptick-cluster/milestones{/number}",
    "notifications_url": "https://api.github.com/repos/uptick/uptick-cluster/notifications{?since,all,participating}",
    "labels_url": "https://api.github.com/repos/uptick/uptick-cluster/labels{/name}",
    "releases_url": "https://api.github.com/repos/uptick/uptick-cluster/releases{/id}",
    "deployments_url": "https://api.github.com/repos/uptick/uptick-cluster/deployments",
    "created_at": 1530439884,
    "updated_at": "2021-05-27T05:19:31Z",
    "pushed_at": 1622093328,
    "git_url": "git://github.com/uptick/uptick-cluster.git",
    "ssh_url": "git@github.com:uptick/uptick-cluster.git",
    "clone_url": "https://github.com/uptick/uptick-cluster.git",
    "svn_url": "https://github.com/uptick/uptick-cluster",
    "homepage": "",
    "size": 12785,
    "stargazers_count": 0,
    "watchers_count": 0,
    "language": "Python",
    "has_issues": true,
    "has_projects": false,
    "has_downloads": true,
    "has_wiki": false,
    "has_pages": false,
    "forks_count": 0,
    "mirror_url": null,
    "archived": false,
    "disabled": false,
    "open_issues_count": 1,
    "license": null,
    "forks": 0,
    "open_issues": 1,
    "watchers": 0,
    "default_branch": "master",
    "stargazers": 0,
    "master_branch": "master",
    "organization": "uptick"
  },
  "pusher": {
    "name": "MonsieurHenry",
    "email": "bot@uptickhq.com"
  },
  "organization": {
    "login": "uptick",
    "id": 10147530,
    "node_id": "MDEyOk9yZ2FuaXphdGlvbjEwMTQ3NTMw",
    "url": "https://api.github.com/orgs/uptick",
    "repos_url": "https://api.github.com/orgs/uptick/repos",
    "events_url": "https://api.github.com/orgs/uptick/events",
    "hooks_url": "https://api.github.com/orgs/uptick/hooks",
    "issues_url": "https://api.github.com/orgs/uptick/issues",
    "members_url": "https://api.github.com/orgs/uptick/members{/member}",
    "public_members_url": "https://api.github.com/orgs/uptick/public_members{/member}",
    "avatar_url": "https://avatars.githubusercontent.com/u/10147530?v=4",
    "description": ""
  },
  "sender": {
    "login": "MonsieurHenry",
    "id": 19162017,
    "node_id": "MDQ6VXNlcjE5MTYyMDE3",
    "avatar_url": "https://avatars.githubusercontent.com/u/19162017?v=4",
    "gravatar_id": "",
    "url": "https://api.github.com/users/MonsieurHenry",
    "html_url": "https://github.com/MonsieurHenry",
    "followers_url": "https://api.github.com/users/MonsieurHenry/followers",
    "following_url": "https://api.github.com/users/MonsieurHenry/following{/other_user}",
    "gists_url": "https://api.github.com/users/MonsieurHenry/gists{/gist_id}",
    "starred_url": "https://api.github.com/users/MonsieurHenry/starred{/owner}{/repo}",
    "subscriptions_url": "https://api.github.com/users/MonsieurHenry/subscriptions",
    "organizations_url": "https://api.github.com/users/MonsieurHenry/orgs",
    "repos_url": "https://api.github.com/users/MonsieurHenry/repos",
    "events_url": "https://api.github.com/users/MonsieurHenry/events{/privacy}",
    "received_events_url": "https://api.github.com/users/MonsieurHenry/received_events",
    "type": "User",
    "site_admin": false
  },
  "created": false,
  "deleted": false,
  "forced": false,
  "base_ref": null,
  "compare": "https://github.com/uptick/uptick-cluster/compare/2a2afbf3a9d8...1d5a9a823e1b",
  "commits": [
    {
      "id": "1d5a9a823e1b9b90f1976b357d0f2913c9a46d10",
      "tree_id": "a63464008bbef87901b687cf7a72e5e06092d845",
      "distinct": true,
      "message": "Updating QA APP: qa-wf-3853",
      "timestamp": "2021-05-27T05:28:46Z",
      "url": "https://github.com/uptick/uptick-cluster/commit/1d5a9a823e1b9b90f1976b357d0f2913c9a46d10",
      "author": {
        "name": "umi",
        "email": "50252935+dreadera@users.noreply.github.com",
        "username": "dreadera"
      },
      "committer": {
        "name": "umi",
        "email": "50252935+dreadera@users.noreply.github.com",
        "username": "dreadera"
      },
      "added": [

      ],
      "removed": [

      ],
      "modified": [
        "apps/qa-wf-3853/deployment.yml"
      ]
    }
  ],
  "head_commit": {
    "id": "1d5a9a823e1b9b90f1976b357d0f2913c9a46d10",
    "tree_id": "a63464008bbef87901b687cf7a72e5e06092d845",
    "distinct": true,
    "message": "Updating QA APP: qa-wf-3853",
    "timestamp": "2021-05-27T05:28:46Z",
    "url": "https://github.com/uptick/uptick-cluster/commit/1d5a9a823e1b9b90f1976b357d0f2913c9a46d10",
    "author": {
      "name": "umi",
      "email": "50252935+dreadera@users.noreply.github.com",
      "username": "dreadera"
    },
    "committer": {
      "name": "umi",
      "email": "50252935+dreadera@users.noreply.github.com",
      "username": "dreadera"
    },
    "added": [

    ],
    "removed": [

    ],
    "modified": [
      "apps/qa-wf-3853/deployment.yml"
    ]
  }
}"""
)


headers = {
    "Request URL": "https://gitops.theo.onuptick.com:",
    "Request method": "POST",
    "Accept": "*/*",
    "content-type": "application/json",
    "User-Agent": "GitHub-Hookshot/28aa328",
    "X-GitHub-Delivery": "6a2cf12e-beac-11eb-82d5-391a0234a3d4",
    "X-GitHub-Event": "push",
    "X-GitHub-Hook-ID": "292837673",
    "X-GitHub-Hook-Installation-Target-ID": "139318783",
    "X-GitHub-Hook-Installation-Target-Type": "repository",
    "X-Hub-Signature": "sha1=12ff19806fc71191137bc1749f7574c228a0a9c3",
    "X-Hub-Signature-256": ("sha256=37c6aa3564905378207c2eb9b29aac5f3ea1803ec0225f983911cc20f7d2e384"),
}
