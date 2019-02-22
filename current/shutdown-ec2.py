"""shutdown-ec2.py"""

__author__ = "Kurt Giessel"
__copyright__ = "Copyright 2019, Highline College"
__license__ = "GPL"
__version__ = "0.1"
__email__ = "kgiessel@highline.edu"

import boto3
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

#variables

#create variables from config.ini
num_teams = (config['TEAMS']['count'])
name_teams = (config['TEAMS']['name'])
aws_region = (config['AWS']['region'])

boto3.setup_default_session(region_name='%s' % (aws_region))
global gbl_ec2resource
gbl_ec2resource = boto3.resource('ec2')
global gbl_ec2client
gbl_ec2client = boto3.client('ec2')

def get_instance_id(team_name):
    filters = [{'Name':'tag:Team', 'Values':[(team_name)]}]
    team_instances = list(gbl_ec2resource.instances.filter(Filters=filters))
    for t in team_instances:
        instance_id = t.instance_id
        print(instance_id)

get_instance_id("Blackteam")

#main
#team_number = 0
#while team_number <= int(num_teams):
#    if team_number < 10:
#        team_name = '%s0%s' % (name_teams, team_number)
#    else:
#        team_name = '%s%s' % (name_teams, team_number)
