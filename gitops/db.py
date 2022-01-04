import asyncio
import base64
import datetime
import os
import random
import time

import boto3
import dsnparse
from invoke import run, task

from .utils import kube
from .utils.apps import get_app_details
from .utils.cli import progress, success, warning

# TODO: Abstract this code out of gitops.


#####################
# DATABASE COMMANDS #
#####################
@task
def backup(ctx, app_name):
    """Backup production or staging database."""
    values = {"name": f"{app_name}-backup", "app": app_name}
    app = get_app_details(app_name, load_secrets=False)
    asyncio.run(
        kube._run_job(
            "jobs/backup-job.yml",
            values,
            context=app.cluster,
            namespace="workforce",
            sequential=True,
        )
    )


@task
def list_backups(ctx, app):
    kube.list_backups("workforce", app)


@task
def restore_backup(ctx, app_name, index, cleanup=True):
    """Restore backed up database."""
    kube.confirm_database(app_name)
    backups = kube.get_backups("workforce", app_name)
    backup = backups[int(index) - 1]
    values = {
        "name": f"{app_name}-restore",
        "timestamp": backup[0],
        "app": app_name,
    }
    app = get_app_details(app_name, load_secrets=False)
    asyncio.run(
        kube._run_job(
            "jobs/restore-job.yml",
            values,
            context=app.cluster,
            namespace="workforce",
            cleanup=cleanup,
        )
    )


@task
def copy_db(ctx, source, destination, skip_backup=False, cleanup=True):
    """Copy database between apps."""
    source_app = get_app_details(source, load_secrets=True)
    destination_app = get_app_details(destination, load_secrets=True)
    kube.confirm_database(destination)
    values = {
        "name": f"copy-db-{source}-{destination}",
        "source": source,
        "destination": destination,
        "SOURCE_DATABASE_URL_ENCODED": source_app.values["secrets"]["DATABASE_URL"],
        "DESTINATION_DATABASE_URL_ENCODED": destination_app.values["secrets"]["DATABASE_URL"],
        "skip_backup": "skip" if skip_backup else "",
    }
    asyncio.run(
        kube._run_job(
            "jobs/copy-db-job.yml",
            values,
            context=source_app.cluster,
            namespace="workforce",
            cleanup=cleanup,
        )
    )
    print(progress("You may want to clear the redis cache now!"))
    print(progress(f"\t- gitops mcommand {destination} clear_cache"))


@task
def download_backup(ctx, app, index=None, path=None, datestamp=False):
    """Download production or staging backup."""
    if not index:
        backups = kube.get_backups("workforce", app)
        if not backups:
            print(warning(f"No backups found for {app}"))
            return
        index = len(backups)
        print(progress("No index specified. Downloading latest backup: " + backups[-1][3]))

    kube.download_backup("workforce", app, index, path, datestamp=datestamp)


@task
def proxy(
    ctx,
    app_name,
    local_port=None,
    bastion_instance_id=None,
    aws_availability_zone=None,
    background=False,
):
    """Creates a proxy to RDS. Can supply either the app name or a DSN

    Usage: gitops db.proxy app_name
    or     gitops db.proxy postgres://...:...@5432/db
    """
    try:
        database_url = app_name
        database_dsn = dsnparse.parse(database_url)
        app_name = database_dsn.user
    except ValueError:
        # app_name was not a valid dsn
        app = get_app_details(app_name, load_secrets=True)
        database_url = base64.b64decode(
            app.values["secrets"]["DATABASE_URL"].encode("ascii")
        ).decode("ascii")
        database_dsn = dsnparse.parse(database_url)

    if not local_port:
        local_port = random.randint(1000, 9999)

    modified_dsn = dsnparse.parse(database_url)
    modified_dsn.hostname = "localhost"
    modified_dsn.port = local_port

    bastion_instance_id = bastion_instance_id or os.environ.get("GITOPS_BASTION_INSTANCE_ID")
    if not bastion_instance_id:
        raise Exception(
            "Please set GITOPS_BASTION_INSTANCE_ID environment variable for db proxy to work."
        )

    aws_availability_zone = aws_availability_zone or os.environ.get("GITOPS_AWS_AVAILABILITY_ZONE")
    if not aws_availability_zone:
        raise Exception(
            "Please set GITOPS_AWS_AVAILABILITY_ZONE environment variable for db proxy to work."
        )

    print(progress(f"Creating a proxy to the RDS instance of: {app_name} "))

    # Create a temporary ssh key
    run("echo -e 'y\n' | ssh-keygen -t rsa -f /tmp/temp -N '' >/dev/null 2>&1")

    # Send ssh key to bastion. These only last 60 seconds
    run(
        f"""aws ec2-instance-connect send-ssh-public-key \
            --instance-id {bastion_instance_id}\
            --availability-zone  {aws_availability_zone} \
            --instance-os-user ec2-user \
            --ssh-public-key file:///tmp/temp.pub
    """,
        hide=True,
    )
    proxy_dsn = modified_dsn.geturl()
    print(progress(f"Connect to the db using: {proxy_dsn}\n"))
    # Create ssh tunnel
    cmd = f"""ssh -i /tmp/temp \
            -N -M -L {local_port}:{database_dsn.hostname}:{database_dsn.port or 5432} \
            -o "UserKnownHostsFile=/dev/null" \
            -o "StrictHostKeyChecking=no" \
            -o "ServerAliveInterval=60" \
            -o ProxyCommand="aws ssm start-session --target %h --document AWS-StartSSHSession --parameters portNumber=%p --region={aws_availability_zone[:-1]}" \
            ec2-user@{bastion_instance_id}"""

    return proxy_dsn, run(cmd, hide=True, asynchronous=background)


@task
def pgcli(
    ctx,
    app_name,
):
    """Opens pgcli to a remote DB"""
    print("making proxy")
    proxy_dsn, ctx = proxy(ctx, app_name, background=True)
    with ctx:
        print("Waiting for proxy to open")
        time.sleep(4)
        run(f"pgcli {proxy_dsn}", pty=True)


@task
def logs(ctx, app_name, last=24):
    """
    Fetches RDS logs since the last N hours.

    Usage:
        gitops db.logs APP --last 5
    """
    rds = boto3.client("rds")
    app = get_app_details(app_name, load_secrets=True)
    db_name = app.name.replace("_", "")
    logs = rds.describe_db_log_files(DBInstanceIdentifier=db_name)
    for log in logs["DescribeDBLogFiles"][-last:]:
        log_file = rds.download_db_log_file_portion(
            DBInstanceIdentifier=db_name,
            LogFileName=log["LogFileName"],
        )
        for line in log_file["LogFileData"].split("\n"):
            if line:
                try:
                    print(
                        str(
                            datetime.datetime.fromisoformat(line[:19])
                            .replace(tzinfo=datetime.timezone.utc)
                            .astimezone()
                        )
                        + line[23:]
                    )
                except Exception:
                    print(line)


@task
def wipe_db(ctx, destination, skip_backup=False, cleanup=True):
    """Wipes a customers database."""
    source_app = get_app_details(destination, load_secrets=True)
    kube.confirm_database(destination)
    values = {
        "name": f"wipe-db-{destination}",
        "destination": destination,
        "SOURCE_DATABASE_URL_ENCODED": source_app.values["secrets"]["DATABASE_URL"],
        "DESTINATION_DATABASE_URL_ENCODED": source_app.values["secrets"]["DATABASE_URL"],
        "skip_backup": "skip" if skip_backup else "",
    }
    print(progress(f":: Wiping database {destination}"))
    asyncio.run(
        kube._run_job(
            "jobs/wipe-db-job.yml",
            values,
            context=source_app.cluster,
            namespace="workforce",
            cleanup=cleanup,
        )
    )
    print(success("Deleted!"))
    print(progress(":: Running migrations"))
    run(f"gitops migrate {destination}", echo=True)

    print(progress(":: Clearing cache"))
    run(f"gitops mcommand {destination} clear_cache", echo=True)

    print(progress("Success!"))
