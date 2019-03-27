"""competition-up.py"""

__author__ = "Kurt Giessel"
__copyright__ = "Copyright 2019, Highline College"
__license__ = "GPL"
__version__ = "0.4"
__email__ = "kgiessel@highline.edu"


import sys
import string
import os


# This is so Django knows where to find stuff.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "iccdi.settings")

# This is so models get loaded.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

from portal.models import *

#import sys
sys.path.insert(0, 'boto3')

#import functions from boto3 directory
from awsconfig import *
from vpc import *
from ec2 import *

if game.router == 'pan':
    from paloalto import *
if game.router == 'vyos':
    from vyos import *
if game.workspaces:
    from workspaces import *


#functions

def create_team(team_number, team_name):
    vpc = create_vpc(team_number, team_name) #create team vpc
    dhcp_set = create_dhcp_set(vpc, team_number, team_name) #create dhcp option set
    ig = create_ig(vpc, team_name) #create team internet gateway
    vpc_peering = create_vpc_peering(vpc, team_name) #create vpc peering to interwebs
    vpc_route_table = create_vpc_route_table(vpc, vpc_peering, ig, team_name) #create vpc route table for teamXX
    cidr = '10.0.%s.0/24' % (team_number)
    add_route(game.interwebs_rtb, vpc_peering, cidr) #add route to interwebs route table for teamXX

    if game.workspaces: #create workspaces subnets and directory if used
        last_octet = 96
        #subnet = create_subnet(vpc, team_number, team_name, last_octet, 'Workspaces1', 'a') #create subnet 1
        #workspaces1_id = subnet.id
        #last_octet += ip_count #get new last octet for cidr
        subnet = create_subnet(vpc, team_number, team_name, last_octet, 'Workstation', 'a') #create subnet 2
        subnet_id = subnet.id
        last_octet += ip_count #get new last octet for cidr
        #create_directory(team_name, vpc, workspaces1_id, workspaces2_id) #create directory
        elastic_ip = create_elastic_ip(team_name) #create elastic ip for nat gateway
        nat_gateway = create_nat_gateway(elastic_ip, subnet_id, team_name) #create nat gateway
        nat_gateway_route_table = create_nat_gateway_route_table(vpc.id, team_name, nat_gateway, vpc_peering) #create nat gateway route table


    last_octet = 0

    subnet_name_array = Subnet.objects.all() #get all subnets from database
    for subnet_name in subnets: #for each subnet in database
        subnet = create_subnet(vpc, team_number, team_name, last_octet, subnet_name.name, 'a') #create subnet
        if game.workspaces:
            associate_route_table(nat_gateway_route_table, subnet) #associate nat gateway route table
        last_octet += ip_count #get new last octet for cidr


    security_group = create_security_group(vpc, team_name, cidr) #create team security groups
    proxy_security_group = create_proxy_security_group(vpc, team_name, cidr)
    create_team_instances(vpc, team_number, team_name, security_group, proxy_security_group) #create all team instances

    ws_number = 1

    while ws_number <= 8:
        create_workstation(team_name, team_number, subnet_id, security_group, proxy_security_group, ws_number)
        ws_number += 1


#main

if game.router == 'pan': #create router subnet (not used yet)
    create_pan_subnet()


team_number = 10

while team_number <= int(game.num_teams): #create each team based on number of teams in database
    if team_number < 10:
        team_name = '%s0%s' % (game.name_teams, team_number) #add ,eading zero to teams 1-9
    else:
        team_name = '%s%s' % (game.name_teams, team_number)
    print('########\nCreateing %s\n########\n' % (team_name))
    create_team(team_number, team_name)
    team_number += 1

print('\n%s teams successfully created (including %s00)' % (team_number, game.name_teams))
