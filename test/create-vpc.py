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
import re
config = configparser.ConfigParser()
config.read('config.ini')

#variables

global event
event = (config['EVENT']['name'])
global aws_region
aws_region = (config['AWS']['region'])
global interwebs_id
interwebs_id = (config['AWS']['interwebs_id'])
global interwebs_cidr
interwebs_cidr = (config['AWS']['interwebs_cidr'])
global domain
domain = (config['TEAMS']['domain'])
num_teams = (config['TEAMS']['count'])
name_teams = (config['TEAMS']['name'])
subnet_name_array = (config.items('SUBNETS'))
subnet_count = len(subnet_name_array)
workspaces = (config['NETWORK']['workspaces'])
router = (config['NETWORK']['router'])



#determine number of subnets and cidr

if workspaces == 'true':
    subnet_count += 2
if router == 'true':
    subnet_count += 1
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
global ec2
ec2 = boto3.resource('ec2')

#functions

def passwd_generator(size=10, chars=string.ascii_letters + string.digits):
    first = random.choice(string.ascii_uppercase)
    last = random.choice(string.digits)
    middle = ''.join(random.choice(chars) for x in range(size))
    return first + middle + last


def create_tags(resource, team_name):
    tag = resource.create_tags(Tags=[{'Key': 'Name', 'Value': '%s' % (team_name)}])
    tag = resource.create_tags(Tags=[{'Key': 'Team', 'Value': '%s' % (team_name)}])
    tag = resource.create_tags(Tags=[{'Key': 'Event', 'Value': '%s' % (event)}])


def create_tags_subnet(subnet, team_name, subnet_name):
    tag = subnet.create_tags(Tags=[{'Key': 'Name', 'Value': '%s-%s' % (team_name, subnet_name)}])
    tag = subnet.create_tags(Tags=[{'Key': 'Team', 'Value': '%s' % (team_name)}])
    tag = subnet.create_tags(Tags=[{'Key': 'Event', 'Value': '%s' % (event)}])


def create_subnet(vpc, team_number, team_name, last_octet, subnet_cidr, subnet_name, event, aws_region, avb_zone):
    #create team subnets
    subnet = vpc.create_subnet(CidrBlock='10.0.%s.%s/%s' % (team_number, last_octet, subnet_cidr), AvailabilityZone='%s%s' % (aws_region, avb_zone))
    create_tags_subnet(subnet, team_name, subnet_name)
    print('Created Subnet %s-%s - %s' % (team_name, subnet_name, subnet.id))

    return subnet


def create_vpc(team_number, team_name, subnet_cidr, ip_count, event, aws_region):
    #create team vpc
    vpc = ec2.create_vpc(CidrBlock='10.0.%s.0/24' % (team_number))
    vpc.wait_until_available()
    create_tags(vpc, team_name)
    print('Created VPC Team%s - %s' % (team_name, vpc.id))

    return vpc


def create_ig(vpc, team_name, event):
    #create and attach internet gateway
    ig = ec2.create_internet_gateway()
    vpc.attach_internet_gateway(InternetGatewayId=ig.id)
    create_tags(ig, team_name)
    print('Created Internet Gateway %s - %s' % (team_name, ig.id))

    return ig


def create_vpc_peering(vpc, interwebs_id, aws_region, team_name, event):
    vpc_peering = vpc.request_vpc_peering_connection(
        PeerVpcId='%s' % (interwebs_id)
    )
    accept_peering_connection = ec2.VpcPeeringConnection('interwebs_id')
    vpc_peering.accept()
    os.system('aws ec2 create-tags --region %s --resources %s --tags Key=Name,Value="%s" Key=Team,Value="%s" Key=Event,Value="%s"' % (aws_region, vpc_peering.id, team_name, team_name, event))
    print('Creating VPC Peering - %s' % (vpc_peering.id))

    return vpc_peering


def create_vpc_route_table(vpc, vpc_peering, ig, team_name, event):
    vpc_route_table = vpc.route_tables.all()
    for t in vpc_route_table:
        vpc_route_table_id = t.route_table_id
    vpc_route_table = ec2.RouteTable('%s' % (vpc_route_table_id))
    vpc_route_table.create_route(
        DestinationCidrBlock='%s' % (interwebs_cidr),
        VpcPeeringConnectionId='%s' % (vpc_peering.id)
    )
    vpc_route_table.create_route(
        DestinationCidrBlock='0.0.0.0/0',
        GatewayId='%s' % (ig.id)
    )
    create_tags(vpc_route_table, team_name)
    print('Created Route Table %s - %s' % (team_name, vpc_route_table_id))

    return vpc_route_table

def create_directory(team_name, vpc, workspaces1_id, workspaces2_id):
    directory_passwd = passwd_generator()
    client = boto3.client('ds')
    directory = client.create_directory(
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

    print('Creating Workspaces Directory ws.%s.%s - %s' % (team_name, domain, directory["DirectoryId"]))
    print('...with password = %s' % (directory_passwd))

    return directory


def create_team(team_number, team_name, subnet_cidr, ip_count, event, aws_region):
    vpc = create_vpc(team_number, team_name, subnet_cidr, ip_count, event, aws_region)
    ig = create_ig(vpc, team_name, event)
    vpc_peering = create_vpc_peering(vpc, interwebs_id, aws_region, team_name, event)
    vpc_route_table = create_vpc_route_table(vpc, vpc_peering, ig, team_name, event)

    last_octet = 0
    #create router subnet if used
    if router == "true":
        subnet = create_subnet(vpc, team_number, team_name, last_octet, subnet_cidr, 'Router', event, aws_region, 'a')
        last_octet += ip_count

    #create workspaces subnet and directory if used
    if workspaces == "true":
        subnet = create_subnet(vpc, team_number, team_name, last_octet, subnet_cidr, 'Workspaces1', event, aws_region, 'a')
        workspaces1_id = subnet.id
        last_octet += ip_count
        subnet = create_subnet(vpc, team_number, team_name, last_octet, subnet_cidr, 'Workspaces2', event, aws_region, 'b')
        workspaces2_id = subnet.id
        last_octet += ip_count
        #create_directory(team_name, vpc, workspaces1_id, workspaces2_id)

    #create subnets
    subnet_name_array = (config.items('SUBNETS'))
    for i in range(len(subnet_name_array)):
        subnet_name = subnet_name_array[i][1]
        subnet = create_subnet(vpc, team_number, team_name, last_octet, subnet_cidr, subnet_name, event, aws_region, 'a')
        last_octet += ip_count

#main

print('################')
print('Creating %s' % (team_name))
print('')
create_team(team_number, team_name, subnet_cidr, ip_count, event, aws_region)
print('')
print('%s Successfully Created!' % (team_name))
print('')
