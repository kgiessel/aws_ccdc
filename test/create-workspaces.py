"""create-workspaces.py"""

__author__ = "Kurt Giessel"
__copyright__ = "Copyright 2018, Highline College"
__license__ = "GPL"
__version__ = "0.1"
__email__ = "kgiessel@highline.edu"

import boto3
import configparser
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

client = boto3.client('ds')
directory = client.create_directory(
    Name='ws.%s.azcatraz.wiz' % (team_name),
    ShortName='%s' % (team_name),
    Password='TempPass123',
    Description='%s' % (team_name),
    Size='Small',
    VpcSettings={
        'VpcId': 'vpc-0354492eeb33c178d',
        'SubnetIds': [
            'subnet-0eea9bf41efd232bf',
            'subnet-09fe2e2aceaa8aa7b',
        ]
    }
)
