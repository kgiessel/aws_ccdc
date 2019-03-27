''' boto3 aws create workstations  '''

import boto3
import sys
import string

def create_instance(team_name, team_number, subnet_id, instance, security_group, proxy_security_group):
    if instance.proxy:
        ec2instance = boto3config.ec2resource.create_instances(
            ImageId=(instance.ami),
            InstanceType=(instance.type),
            KeyName=(team_name),
            SecurityGroupIds=[(security_group.id),(proxy_security_group.id)],
            SubnetId=(subnet_id),
            PrivateIpAddress='10.0.%s.%s' % (team_number, instance.ip),
            MaxCount=1,
            MinCount=1
        )
