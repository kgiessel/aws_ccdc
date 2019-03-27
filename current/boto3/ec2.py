''' boto3 ec2 functions '''

from awsconfig import *
import os

def create_security_group(vpc, team_name, cidr):
    #create a security group for the team
    security_group = boto3config.ec2client.create_security_group(
        Description = '%s Default Security Group' % (team_name),
        GroupName = (team_name),
        VpcId = (vpc.id)
    )
    #set security group ingress rules
    security_group = boto3config.ec2resource.SecurityGroup(security_group['GroupId'])
    security_group.authorize_ingress(
        CidrIp = (game.interwebs_cidr),
        IpProtocol = '-1',
        ToPort = -1
    )
    security_group.authorize_ingress(
        CidrIp = (cidr),
        IpProtocol = '-1',
        ToPort = -1
    )
    security_group.revoke_egress(
        IpPermissions=[
            {
                'IpRanges': [ { 'CidrIp': '0.0.0.0/0'}, ],
                'IpProtocol': '-1',
                'ToPort': -1
            }
        ]
    )
    security_group.authorize_egress(
        IpPermissions=[
            {
                'IpRanges': [ { 'CidrIp': (game.interwebs_cidr)}, ],
                'IpProtocol': '-1',
                'ToPort': -1
            }
        ]
    )
    security_group.authorize_egress(
        IpPermissions=[
            {
                'IpRanges': [ { 'CidrIp': (cidr)}, ],
                'IpProtocol': '-1',
                'ToPort': -1
            }
        ]
    )
    security_group.authorize_egress(
        IpPermissions=[
            {
                'IpRanges': [ { 'CidrIp': '0.0.0.0/0'}, ],
                'IpProtocol': 'udp',
                'FromPort': 53,
                'ToPort': 53
            }
        ]
    )
    if not game.workspaces:
        security_group.authorize_ingress(
            CidrIp = '0.0.0.0/0',
            IpProtocol = 'tcp',
            FromPort = 3389,
            ToPort = 3389
            )
        security_group.authorize_ingress(
            CidrIp = '0.0.0.0/0',
            IpProtocol = 'tcp',
            FromPort = 22,
            ToPort = 22
            )
    create_tags(security_group, team_name)
    create_log(team_name, 'Security Group %s' % (team_name), security_group.id)

    return security_group


def create_proxy_security_group(vpc, team_name, cidr):
    #create a security group for the team
    proxy_security_group = boto3config.ec2client.create_security_group(
        Description = '%s Web Access Security Group' % (team_name),
        GroupName = '%s-WebAccess' % (team_name),
        VpcId = (vpc.id)
    )
    #set security group ingress rules
    proxy_security_group = boto3config.ec2resource.SecurityGroup(proxy_security_group['GroupId'])
    proxy_security_group.authorize_ingress(
        CidrIp = '168.156.71.0/24',
        IpProtocol = 'tcp',
        FromPort = 3389,
        ToPort = 3389
        )
    proxy_security_group.revoke_egress(
        IpPermissions=[
            {
                'IpRanges': [ { 'CidrIp': '0.0.0.0/0'}, ],
                'IpProtocol': '-1',
                'ToPort': -1
            }
        ]
    )
    proxy_security_group.authorize_egress(
        IpPermissions=[
            {
                'IpRanges': [ { 'CidrIp': '0.0.0.0/0'}, ],
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80
            }
        ]
    )
    proxy_security_group.authorize_egress(
        IpPermissions=[
            {
                'IpRanges': [ { 'CidrIp': '0.0.0.0/0'}, ],
                'IpProtocol': 'tcp',
                'FromPort': 443,
                'ToPort': 443
            }
        ]
    )
    nametag = '%s-WebAccess' % (team_name)
    create_tags(proxy_security_group, nametag)
    create_log(team_name, 'Security Group %s' % (team_name), proxy_security_group.id)

    return proxy_security_group


#get instance config for each instance
def create_team_instances(vpc, team_number, team_name, security_group, proxy_security_group):
    #create team keypair
    create_keypair(team_name)
    #for each instance in instances db
    instances = Instance.objects.all()
    for instance in instances:
        filters = [{'Name':'tag:Name', 'Values':['%s-%s' % (team_name, instance.subnet)]}]
        subnet_id = list(boto3config.ec2resource.subnets.filter(Filters=filters))
        for t in subnet_id:
            subnet_id = t.subnet_id
        create_instance(team_name, team_number, subnet_id, instance, security_group, proxy_security_group)


#create the instance
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
    else:
        ec2instance = boto3config.ec2resource.create_instances(
            ImageId=(instance.ami),
            InstanceType=(instance.type),
            KeyName=(team_name),
            SecurityGroupIds=[(security_group.id)],
            SubnetId=(subnet_id),
            PrivateIpAddress='10.0.%s.%s' % (team_number, instance.ip),
            MaxCount=1,
            MinCount=1
        )
    for t in ec2instance:
        instance_id = t.instance_id
    ec2instance = boto3config.ec2resource.Instance(instance_id)

    instance_name='%s-%s' % (team_name, instance.name)
    tag = ec2instance.create_tags(Tags=[
        {'Key': 'Name', 'Value': '%s' % (instance_name)},
        {'Key': 'Team', 'Value': '%s' % (team_name)},
        {'Key': 'Event', 'Value': '%s' % (game.event)}
    ])

    filename = "%s-log.txt" % (team_name)
    file = open(filename,"a")
    file.writelines('Creating Instance %s\n' % (instance_name))
    print('Creating Instance %s' % (instance_name))
    file.writelines('\ton subnet %s-%s - %s\n' % (team_name, instance.subnet, subnet_id))
    print('\ton subnet %s-%s - %s' % (team_name, instance.subnet, subnet_id))
    file.writelines('\tIP: 10.0.%s.%s\n' % (team_number, instance.ip))
    print('\tIP: 10.0.%s.%s' % (team_number, instance.ip))
    file.writelines('\tType: %s\n' % (instance.type))
    print('\tType: %s' % (instance.type))

    #if not using workspaces, create elastic ip and dns
    if not game.workspaces:
        create_external_dns(ec2instance, instance_id, instance_name, team_name, instance.name)
    internal_ip = '10.0.%s.%s' % (team_number, instance.ip)
    create_internal_dns(instance_name, team_name, instance, internal_ip)

    file.writelines('\n')
    file.close()


def create_workstation(team_name, team_number, subnet_id, security_group, proxy_security_group, ws_number):
    filters = [{'Name':'tag:Name', 'Values':['%s-Workstation' % (team_name)]}]
    subnet_id = list(boto3config.ec2resource.subnets.filter(Filters=filters))
    for t in subnet_id:
        subnet_id = t.subnet_id
    ec2instance = boto3config.ec2resource.create_instances(
        ImageId='ami-0bde65d420b25896a',
        InstanceType='t2.medium',
        KeyName=(team_name),
        SecurityGroupIds=[(security_group.id),(proxy_security_group.id)],
        SubnetId=(subnet_id),
        MaxCount=1,
        MinCount=1
        )
    for t in ec2instance:
        instance_id = t.instance_id
    ec2instance = boto3config.ec2resource.Instance(instance_id)

    instance_name = '%s-Workstation-%s' % (team_name, ws_number)
    tag = ec2instance.create_tags(Tags=[
        {'Key': 'Name', 'Value': '%s' % (instance_name)},
        {'Key': 'Team', 'Value': '%s' % (team_name)},
        {'Key': 'Event', 'Value': '%s' % (game.event)}
    ])
    print('Creating Instance %s' % (instance_name))
    dns_name = 'ws%s' % (ws_number)

    create_external_dns(ec2instance, instance_id, instance_name, team_name, dns_name)


#create elastic ip and dns
def create_external_dns(ec2instance, instance_id, instance_name, team_name, dns_name):
    elastic_ip = boto3config.ec2client.allocate_address()
    #create tag for elastic ip - boto3 doesn't have a create_tags class for elastic ip
    os.system('aws ec2 create-tags --region %s --resources %s --tags Key=Name,Value="%s" Key=Team,Value="%s" Key=Event,Value="%s"' % (game.aws_region, elastic_ip['AllocationId'], instance_name, team_name, game.event))
    filename = "%s-log.txt" % (team_name)
    file = open(filename,"a")
    file.writelines('\tPublic IP: %s\n' % (elastic_ip['PublicIp']))
    file.close()
    print('\tPublic IP: %s' % (elastic_ip['PublicIp']))
    print('Waiting for instance to be in running state')
    #wait until instance is running before associating elastic IP
    ec2instance.wait_until_running()
    assign_eip = boto3config.ec2client.associate_address(
        AllocationId=(elastic_ip['AllocationId']),
        InstanceId=(instance_id)
    )
    #create route53 dns record
    route53 = boto3.client('route53')
    dns_record = route53.change_resource_record_sets(
        HostedZoneId='Z1BBVC5HFAK3WL', #needs to be added to database - hardcoded for now
        ChangeBatch={
            'Comment': (instance_name),
            'Changes': [
                {
                    'Action': 'CREATE',
                    'ResourceRecordSet': {
                        'Name': '%s.%s.prccdc.org' % (dns_name, team_name),
                        'Type': 'A',
                        'TTL': 60,
                        'ResourceRecords': [
                            {
                                'Value' : (elastic_ip['PublicIp'])
                            },
                        ],
                    }
                },
            ]
        }
    )


def create_internal_dns(instance_name, team_name, instance, internal_ip):
    #create route53 dns record
    route53 = boto3.client('route53')
    dns_record = route53.change_resource_record_sets(
        HostedZoneId=(game.route53_zone),
        ChangeBatch={
            'Comment': (instance_name),
            'Changes': [
                {
                    'Action': 'CREATE',
                    'ResourceRecordSet': {
                        'Name': '%s.%s.%s' % (instance.name, team_name, game.domain),
                        'Type': 'A',
                        'TTL': 60,
                        'ResourceRecords': [
                            {
                                'Value' : (internal_ip)
                            },
                        ],
                    }
                },
            ]
        }
    )
