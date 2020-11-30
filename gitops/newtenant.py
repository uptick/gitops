from invoke import run, task
from pathlib import Path

import boto3

from .utils import gen_secret, yaml
from .utils.cli import confirm, progress, success, success_negative, warning
from .utils.images import get_latest_image

######################
# NEWTENANT COMMANDS #
#####################################################################################
# NOTE: These should live in uptick-cluster repo, not in the public-facing gitops.. #
#####################################################################################


@task
def new_tenant(ctx, name, db_name=None, tags='', prefix='unset'):
    """ Create a new tenant.

    Creates a database, an IAM user, and fills in a new template. Once this
    command finishes the repository needs to be committed and pushed in order
    for the new tenant to be provisioned.

    Full list of tags:
    - `workforce/maintenance/compliance` - the code that the app is serving; random services do not have this tag
    - `customer/internal` - informs who is using the app
    - `sandbox/production` - informs whether or not the app is used for testing purposes
    - `enterprise` - customer receives a better db, more/stronger workers and a sandbox server
    - `dedicated` - customer's contract stipulates their data is to be hosted in isolation
    - `preview` - customer is looking at a preview of what they might have, but hasn't signed yet
    - `onboarding` - customer has signed and is now onboarding, making them potentially eligible to have a temporary sandbox server.
    - `fast_release` - receives the release a few days prior to other apps
    - `slow_release` - receives the release a week after other apps

    Examples:
    inv new-tenant arawater --tags workforce,customer,production,enterprise --prefix emeriss
    inv new-tenant demo-water --tags workforce,internal,sandbox --prefix falkor
    inv new-tenant wisercommunities --tags maintenance,customer,production,preview --prefix ipsum
    """
    run_new_tenant_checks(ctx, name)
    if db_name is None:
        db_name = name
    if '-' in db_name:
        print(warning(f"The db_name cannot contain hyphens. These will be removed: {db_name} -> {db_name.replace('-', '')}"))
        if not confirm():
            print(success_negative("Operation aborted. Invalid database name. Specify a name with the `--db-name` flag."))
            return
        db_name = db_name.replace('-', '')
    tags = tags.split(',') if tags else []
    context = {
        'database_url': create_database(ctx, db_name),
        **create_iam_user(ctx, name, internal='internal' in tags),
        'name': name,
        'image_prefix': prefix,
        'secret_key': gen_secret(32),
        'tags': tags,
    }
    create_app_configs(context)
    run(f'git add apps/{name}/')
    run(f'git commit -m "Spin up new app: {name}."')
    print(success('Done!'))
    print(warning('Type `git push` to complete the deployment of this app.'))
    print(progress('You may want to run migrations after this, or copy an existing database across!'))
    print(progress('If you do the former, remember to run reset_support_account at the end.'))
    print(warning(
        f'Remember to add "{name}" as a new Authorized URI Redirect in the Google API console '
        'under API OAuth client Credentials. Link can be found here: '
        'https://console.developers.google.com/apis/credentials?project=support-account--1554422451604'
    ))


@task
def create_database(ctx, name, storage=10, backup=7, show=False):
    """ Create an RDS database for a new tenant.
    """
    print(progress('Creating database ... '), end='', flush=True)
    instance_name = name
    boto3.setup_default_session(region_name='ap-southeast-2')
    password = gen_secret(32)
    ec2 = boto3.resource('ec2')
    # Find the security group for the nodes.
    for sg in ec2.security_groups.all():
        if sg.group_name == 'uptick-db-private':
            break
    else:
        raise Exception('Unable to find security group.')
    sg_id = sg.id
    # Create the database.
    rds = boto3.client('rds')
    rds.create_db_instance(
        DBName=instance_name,
        DBInstanceIdentifier=instance_name,
        DBInstanceClass='db.t3.micro',
        Engine='postgres',
        AllocatedStorage=storage,
        StorageType='gp2',
        MasterUsername=name,
        MasterUserPassword=password,
        BackupRetentionPeriod=backup,
        DBSubnetGroupName='uptick-db-private',
        VpcSecurityGroupIds=[sg_id],
        PubliclyAccessible=False,
        Tags=[
            {
                'Key': 'group',
                'Value': 'workforce'
            }
        ]
    )
    print('ok')
    print(progress('Waiting for DB to go live ... '), end='', flush=True)
    waiter = rds.get_waiter('db_instance_available')
    waiter.wait(
        DBInstanceIdentifier=instance_name
    )
    print('ok')
    print(progress('Retrieving DB details ... '), end='', flush=True)
    result = rds.describe_db_instances(DBInstanceIdentifier=instance_name)
    result = result['DBInstances'][0]
    user = result['MasterUsername']
    dbname = result['DBName']
    endpoint = result['Endpoint']['Address']
    port = result['Endpoint']['Port']
    database_url = f'postgres://{user}:{password}@{endpoint}:{port}/{dbname}'
    print('ok')
    if show:
        print(database_url)
    return database_url


@task
def create_iam_user(ctx, name, internal=False, show=False):
    """ Create an IAM user for a new tenant.

    We don't need to create a group, because new customers all use a global S3
    bucket nowadays.
    """
    print(progress('Creating IAM user ... '), end='', flush=True)
    iam = boto3.resource('iam')
    user = iam.User(name)
    user.create(Path='/workforce/')
    group = 'servers-internal' if internal else 'servers-customer'
    user.add_group(GroupName=group)
    access_key = user.create_access_key_pair()
    access_key_dict = {
        'aws_key': access_key.id,
        'aws_secret': access_key.secret
    }
    print('ok')
    if show:
        print(access_key_dict)
    return access_key_dict


@task
def run_new_tenant_checks(ctx, name):
    print(progress('Running new tenant checks ... '), end='', flush=True)
    if not Path('apps').exists():
        raise Exception("Could not find an 'apps' directory. Are you in a cluster repo?")
    if Path(f'apps/{name}').exists():
        raise Exception("Tenant directory already exists!")
    print('ok')


def create_app_configs(context):
    print(progress('Creating app config files ... '), end='', flush=True)
    name = context['name']
    Path(f"apps/{name}").mkdir()
    image_prefix = context['image_prefix']
    image_tag = get_latest_image(image_prefix)
    if image_tag is None:
        print(warning(f"Unable to find image tag with prefix {image_prefix}. You'll need to bump the image before you can deploy."))
        image_tag = image_prefix
    deployment = {
        'extends': '../deployment.yml',
        'tags': context['tags'],
        'image-tag': image_tag,
    }
    secrets = {
        'secrets': {
            'AWS_ACCESS_KEY_ID': context['aws_key'],
            'AWS_SECRET_ACCESS_KEY': context['aws_secret'],
            'DATABASE_URL': context['database_url'],
            'SECRET_KEY': context['secret_key'],
        },
    }
    with open(Path('apps') / name / 'deployment.yml', 'w') as f:
        yaml.dump(deployment, f, default_flow_style=False)
    with open(Path('apps') / name / 'secrets.yml', 'w') as f:
        yaml.dump(secrets, f, default_flow_style=False)
    print('ok')


@task
def delete_tenant(ctx):
    """ We're scared of automating this atm, so just print steps to fully deleting a tenant. """
    print(progress("\t- Delete customer folder in uptick-cluster to remove the deployment from k8s."))
    print(progress("\t- Route53: Delete RecordSets"))
    print(progress("\t- RDS: Delete Database (and Subnet if DB wasn't using a shared one)"))
    print(progress("\t- IAM: Delete User (and related Group if legacy customer)"))
    print(progress("\t- S3: Archive and Delete Bucket/Folder; Delete correspondence folder"))
    print(progress("\t- SES: Delete Rule Sets (SES Oregon -> Active Rule Set)"))
    print(progress("\t- Delete Authorized URI Redirect in the Google API console under API OAuth client Credentials."))
    print(progress("\t- Delete Papertrail systems."))
