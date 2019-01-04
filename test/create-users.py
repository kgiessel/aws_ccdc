"""create-users.py"""

__author__ = "Kurt Giessel"
__copyright__ = "Copyright 2018, Highline College"
__license__ = "GPL"
__version__ = "0.1"
__email__ = "kgiessel@highline.edu"

import boto3
import configparser
import string
import random
config = configparser.ConfigParser()
config.read('config.ini')

event = (config['EVENT']['name'])
aws_region =  (config['AWS']['region'])
num_teams = (config['TEAMS']['count'])
name_teams = (config['TEAMS']['name'])
subnet_name_array = (config.items('SUBNETS'))
subnet_count = len(subnet_name_array)
workspaces = (config['NETWORK']['workspaces'])
router = (config['NETWORK']['router'])

boto3.setup_default_session(region_name='%s' % (aws_region))

team_number = 0
if team_number < 10:
    team_name = '%s0%s' % (name_teams, team_number)
else:
    team_name = '%s%s' % (name_teams, team_number)

def passwd_generator(size=10, chars=string.ascii_letters + string.digits):
    first = random.choice(string.ascii_uppercase)
    last = random.choice(string.digits)
    middle = ''.join(random.choice(chars) for x in range(size))
    return first + middle + last

def create_tags(resource, team_name, event):
    tag = resource.create_tags(Tags=[{'Key': 'Name', 'Value': '%s' % (team_name)}])
    tag = resource.create_tags(Tags=[{'Key': 'Team', 'Value': '%s' % (team_name)}])
    tag = resource.create_tags(Tags=[{'Key': 'Event', 'Value': '%s' % (event)}])

#iam = boto3.client('iam')
#response = iam.create_user(
#    UserName='%s' % (team_name)
#)
#print(response)

ec2 = boto3.resource('ec2')
stuff = ec2.get_available_subresources()
print(stuff)
