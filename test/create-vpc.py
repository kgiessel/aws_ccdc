"""create-vpc.py"""

__author__ = "Kurt Giessel"
__copyright__ = "Copyright 2018, Highline College"
__license__ = "GPL"
__version__ = "0.1"
__email__ = "kgiessel@highline.edu"

import boto3
import configparser
import string
import random
import os
import json
config = configparser.ConfigParser()
config.read('config.ini')

#variables

#create variables from config.ini
global event
event = (config['EVENT']['name'])
global aws_region
aws_region = (config['AWS']['region'])
global interwebs_id
interwebs_id = (config['AWS']['interwebs_id'])
global interwebs_cidr
interwebs_cidr = (config['AWS']['interwebs_cidr'])
global interwebs_rtb
interwebs_rtb = (config['AWS']['interwebs_rtb'])
global domain
domain = (config['TEAMS']['domain'])
num_teams = (config['TEAMS']['count'])
name_teams = (config['TEAMS']['name'])
subnet_name_array = (config.items('SUBNETS'))
subnet_count = len(subnet_name_array)
global workspaces
workspaces = (config['NETWORK']['workspaces'])
global router
router = (config['NETWORK']['router'])
global route53_zone
route53_zone = (config['AWS']['route53_zone'])

#determine number of subnets and cidr for team vpc
#add 2 subnets is workspaces are used
global subnet_cidr
if workspaces == 'true':
    subnet_count += 2
if subnet_count == 1:
    subnet_cidr = 24
    ip_count = 256
if subnet_count == 2:
    subnet_cidr = 25
    ip_count = 128
if subnet_count == 3 or subnet_count == 4:
    subnet_cidr = 26
    ip_count = 64
if subnet_count >= 5 and subnet_count <=8:
    subnet_cidr = 27
    ip_count = 32

team_number = 0
if team_number < 10:
    team_name = '%s0%s' % (name_teams, team_number)
else:
    team_name = '%s%s' % (name_teams, team_number)

boto3.setup_default_session(region_name='%s' % (aws_region))
global gbl_ec2resource
gbl_ec2resource = boto3.resource('ec2')
global gbl_ec2client
gbl_ec2client = boto3.client('ec2')

#functions

def passwd_generator(size=10, chars=string.ascii_letters + string.digits):
        #generate a 12 character password beginning with a capital letter and ending in a number
    first = random.choice(string.ascii_uppercase)
    last = random.choice(string.digits)
    middle = ''.join(random.choice(chars) for x in range(size))

    return first + middle + last


def create_keypair(team_name):
    keypair = gbl_ec2client.create_key_pair(KeyName='%s' % (team_name))
    create_log(team_name, 'Private Key %s \n\n' % (team_name), keypair['KeyMaterial'])


def create_log(team_name, desc, log):
    filename = "%s-log.txt" % (team_name)
    file = open(filename,"a")
    file.writelines(desc)
    file.writelines(' - ')
    file.writelines(log)
    file.writelines('\n\n')
    file.close()
    print('Created %s' % (desc))


def create_tags(resource, tag_name):
        #create name, team, and event tags
    tag = resource.create_tags(Tags=[
        {'Key': 'Name', 'Value': '%s' % (tag_name)},
        {'Key': 'Team', 'Value': '%s' % (tag_name)},
        {'Key': 'Event', 'Value': '%s' % (event)}
    ])


def create_subnet(vpc, team_number, team_name, last_octet, subnet_name, avb_zone):
        #create team subnets with appropriate cidr block for class c vpc based on number of subnets needed
    subnet = vpc.create_subnet(CidrBlock='10.0.%s.%s/%s' % (team_number, last_octet, subnet_cidr), AvailabilityZone='%s%s' % (aws_region, avb_zone))
    subnet_tag_name = '%s-%s' % (team_name, subnet_name)
    create_tags(subnet, subnet_tag_name)
    create_log(team_name, 'Subnet %s-%s' % (team_name, subnet_name), subnet.id)

    return subnet


def create_vpc(team_number, team_name):
        #create team vpc with cidr block 10.0.n.0/24 where n = team number
    vpc = gbl_ec2resource.create_vpc(CidrBlock='10.0.%s.0/24' % (team_number))
    vpc.wait_until_available()
    create_tags(vpc, team_name)
    create_log(team_name, 'VPC %s' % (team_name), vpc.id)

    return vpc


def create_ig(vpc, team_name):
        #create and attach internet gateway
    ig = gbl_ec2resource.create_internet_gateway()
    vpc.attach_internet_gateway(InternetGatewayId=ig.id)
    create_tags(ig, team_name)
    create_log(team_name, 'Internet Gateway %s' % (team_name), ig.id)

    return ig


def create_vpc_peering(vpc, team_name):
        #request a peering connection to the interwebs vpc
    vpc_peering = vpc.request_vpc_peering_connection(
        PeerVpcId='%s' % (interwebs_id)
    )
        #accept the peering request
    accept_peering_connection = gbl_ec2resource.VpcPeeringConnection('interwebs_id')
    vpc_peering.accept()
        #create tag for peering connection - boto3 doesn't have a create_tags class for vpc peering
    os.system('aws ec2 create-tags --region %s --resources %s --tags Key=Name,Value="%s" Key=Team,Value="%s" Key=Event,Value="%s"' % (aws_region, vpc_peering.id, team_name, team_name, event))
    create_log(team_name, 'Peering Connection %s' % (team_name), vpc_peering.id)

    return vpc_peering


def create_vpc_route_table(vpc, vpc_peering, ig, team_name):
        #get the route table id for the route table attached to the created vpc
    vpc_route_table = vpc.route_tables.all()
    for t in vpc_route_table:
        vpc_route_table_id = t.route_table_id
        #add route to vpc peering connection for interwebs traffic
    route = gbl_ec2resource.RouteTable('%s' % (vpc_route_table_id))
    route.create_route(
        DestinationCidrBlock='%s' % (interwebs_cidr),
        VpcPeeringConnectionId='%s' % (vpc_peering.id)
    )
        #add default route to internet gateway
    route.create_route(
        DestinationCidrBlock='0.0.0.0/0',
        GatewayId='%s' % (ig.id)
    )
    create_tags(route, team_name)
    create_log(team_name, 'Route Table %s' % (team_name), vpc_route_table_id)

def add_route(rtb, destination, cidr):
        #add a route to a route table
    route = gbl_ec2resource.RouteTable('%s' % (rtb))
    route.create_route(
        DestinationCidrBlock='%s' % (cidr),
        VpcPeeringConnectionId='%s' % (destination.id)
    )


def create_directory(team_name, vpc, workspaces1_id, workspaces2_id):
        #create a simple ad directory for aws workspaces
    directory_passwd = passwd_generator()
    ds = boto3.client('ds')
    directory = ds.create_directory(
        Name='ws.%s.%s' % (team_name, domain),
        ShortName='%s' % (team_name),
        Password='%s' % (directory_passwd),
        Description='%s' % (team_name),
        Size='Small',
        VpcSettings={
            'VpcId': '%s' % (vpc.id),
            'SubnetIds': [
                '%s' % (workspaces1_id),
                '%s' % (workspaces2_id),
            ]
        }
    )
    create_log(team_name, 'Workspace Directory', 'ws.%s.%s' % (team_name, domain), directory["DirectoryId"])
    create_log(team_name, 'Directory Password', directory_passwd)


    return directory


def create_security_group(vpc, team_name):
    security_group = gbl_ec2client.create_security_group(
        Description = '%s Default Security Group' % (team_name),
        GroupName = '%s' % (team_name),
        VpcId = '%s' % (vpc.id)
    )
    security_group = gbl_ec2resource.SecurityGroup(security_group['GroupId'])
    security_group.authorize_ingress(
        CidrIp = '0.0.0.0/0',
        IpProtocol = '-1',
        ToPort = -1
    )
    create_tags(security_group, team_name)
    create_log(team_name, 'Security Group %s' % (team_name), security_group.id)

    return security_group


def get_instance_config(vpc, team_number, team_name, security_group):
        #create instance for team_name
    instance_array = (config.items('INSTANCES'))
        #for each subnet in config.ini [INSTANCES]
    for i in range(len(instance_array)):
        instance = (json.loads(instance_array[i][1]))
        filters = [{'Name':'tag:Name', 'Values':['%s-%s' % (team_name, instance['subnet'])]}]
        subnet_id = list(gbl_ec2resource.subnets.filter(Filters=filters))
        for t in subnet_id:
            subnet_id = t.subnet_id
        create_instance(team_name, team_number, subnet_id, instance, security_group)


def create_instance(team_name, team_number, subnet_id, instance, security_group):
    ec2instance = gbl_ec2resource.create_instances(
        ImageId='%s' % (instance['ami']),
        InstanceType='%s' % (instance['type']),
        KeyName='%s' % (team_name),
        SecurityGroupIds=['%s' % (security_group.id)],
        SubnetId='%s' % (subnet_id),
        PrivateIpAddress='10.0.%s.%s' % (team_number, instance['ip']),
        MaxCount=1,
        MinCount=1
    )
    for t in ec2instance:
        instance_id = t.instance_id
    ec2instance = gbl_ec2resource.Instance(instance_id)

    instance_name='%s-%s' % (team_name, instance['name'])
    create_tags(ec2instance, instance_name)

    filename = "%s-log.txt" % (team_name)
    file = open(filename,"a")
    file.writelines('Creating Instance %s\n' % (instance_name))
    print('Creating Instance %s' % (instance_name))
    file.writelines('\ton subnet %s-%s - %s\n' % (team_name, instance['subnet'], subnet_id))
    print('\ton subnet %s-%s - %s' % (team_name, instance['subnet'], subnet_id))
    file.writelines('\tIP: 10.0.%s.%s\n' % (team_number, instance['ip']))
    print('\tIP: 10.0.%s.%s' % (team_number, instance['ip']))
    file.writelines('\tType: %s\n' % (instance['type']))
    print('\tType: %s' % (instance['type']))

    if workspaces == "false":
        elastic_ip = gbl_ec2client.allocate_address()
        os.system('aws ec2 create-tags --region %s --resources %s --tags Key=Name,Value="%s" Key=Team,Value="%s" Key=Event,Value="%s"' % (aws_region, elastic_ip['AllocationId'], instance_name, team_name, event))
        file.writelines('\tPublic IP: %s\n' % (elastic_ip['PublicIp']))
        print('\tPublic IP: %s' % (elastic_ip['PublicIp']))
        print('Waiting for instance to be in running state')
        #wait until instance is running before associating elastic IP
        ec2instance.wait_until_running()
        assign_eip = gbl_ec2client.associate_address(
            AllocationId=(elastic_ip['AllocationId']),
            InstanceId=(instance_id)
        )
        route53 = boto3.client('route53')
        create_dns_record = route53.change_resource_record_sets(
            HostedZoneId=(route53_zone),
            ChangeBatch={
                'Comment': (instance_name),
                'Changes': [
                    {
                        'Action': 'CREATE',
                        'ResourceRecordSet': {
                            'Name': '%s.%s.prccdc.org' % (instance['name'], team_name),
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

    file.writelines('\n')

    return ec2instance


def create_team(team_number, team_name):
        #create team vpc
    vpc = create_vpc(team_number, team_name)
        #create team internet gateway
    ig = create_ig(vpc, team_name)
        #create vpc peering to interwebs
    vpc_peering = create_vpc_peering(vpc, team_name)
        #add routes to team route table and tag it
    vpc_route_table = create_vpc_route_table(vpc, vpc_peering, ig, team_name)
        #add route to interwebs route table
    cidr = '10.0.%s.0/24' % (team_number)
    add_route(interwebs_rtb, vpc_peering, cidr)

    last_octet = 0

            #create subnets
    subnet_name_array = (config.items('SUBNETS'))
        #for each subnet in config.ini [SUBNETS]
    for i in range(len(subnet_name_array)):
            #get subnet name
        subnet_name = subnet_name_array[i][1]
        subnet = create_subnet(vpc, team_number, team_name, last_octet, subnet_name, 'a')
            #get new last octet for cidr
        last_octet += ip_count

        #create workspaces subnets and directory if used
    if workspaces == "true":
        subnet = create_subnet(vpc, team_number, team_name, last_octet, 'Workspaces1', 'a')
        workspaces1_id = subnet.id
            #get new last octet for cidr
        last_octet += ip_count
        subnet = create_subnet(vpc, team_number, team_name, last_octet, 'Workspaces2', 'b')
        workspaces2_id = subnet.id
            #get new last octet for cidr
        last_octet += ip_count
        create_directory(team_name, vpc, workspaces1_id, workspaces2_id)

    create_keypair(team_name)
    security_group = create_security_group(vpc, team_name)
    get_instance_config(vpc, team_number, team_name, security_group)



#main

create_team(team_number, team_name)
