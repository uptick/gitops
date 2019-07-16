from invoke import task

import boto3


@task
def update_db_vpc_subnets(ctx):
    ec2 = boto3.resource('ec2')
    # Find the security group for the nodes.
    for sg in ec2.security_groups.all():
        if sg.group_name == 'nodes.uptick.k8s.local':
            break
    else:
        raise Exception('Unable to find security group.')
    sg_id = sg.id

    rds = boto3.client('rds')
    dbs = rds.describe_db_instances()
    for db in dbs['DBInstances']:
        # Skip anything related to bSecure
        if 'bsecure' in db['DBInstanceIdentifier']:
            continue

        # Find any dbs using dead subnet and swap them out.
        if db['DBSubnetGroup']['VpcId'] == 'vpc-039de764':
            print('Updating ' + db['DBInstanceIdentifier'])

            try:
                rds.modify_db_instance(
                    DBInstanceIdentifier=db['DBInstanceIdentifier'],
                    DBSubnetGroupName='uptick.k8s.local',
                    VpcSecurityGroupIds=[sg_id],
                    ApplyImmediately=True,
                )
            except Exception as e:
                # If db is in AZ 2c, put on bsecure subnet for now.
                if db['AvailabilityZone'] == 'ap-southeast-2c':
                    try:
                        rds.modify_db_instance(
                            DBInstanceIdentifier=db['DBInstanceIdentifier'],
                            DBSubnetGroupName='default',
                            VpcSecurityGroupIds=['sg-7d56881a'],
                            ApplyImmediately=True,
                        )
                    except Exception as e:
                        print('Failed to update ' + db['DBInstanceIdentifier'] + str(e))
                else:
                    print('Failed to update ' + db['DBInstanceIdentifier'] + str(e))
