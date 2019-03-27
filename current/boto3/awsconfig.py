''' boto3 aws functions '''

import boto3
import sys
import string
import random
from portal.models import *


#game config from django portal db
class GameConfig:
    def __init__(self):
        gameinfo = Gameinfo.objects.all()
        for gameinfo in gameinfo:
            self.event = gameinfo.event
            self.aws_region = gameinfo.region
            self.interwebs_id = gameinfo.interwebs_id
            self.interwebs_cidr = gameinfo.interwebs_cidr
            self.interwebs_rtb = gameinfo.interwebs_rtb
            self.domain = gameinfo.domain
            self.num_teams = gameinfo.num_teams
            self.name_teams = gameinfo.name_teams
            self.workspaces = gameinfo.workspaces
            self.router = gameinfo.router
            self.route53_zone = gameinfo.route53_zone

game = GameConfig()


# boto3 config
class Boto3Config:
    def __init__(self):
        boto3.setup_default_session(region_name=game.aws_region)
        self.ec2resource = boto3.resource('ec2')
        self.ec2client = boto3.client('ec2')

boto3config = Boto3Config()


#determine number of subnets and cidr for team vpc
#add 2 subnets is workspaces are used
subnets = Subnet.objects.all()
subnet_count = len(subnets)
global subnet_cidr
#if game.workspaces:
#    subnet_count += 2
#if subnet_count == 1:
#    subnet_cidr = 24
#    ip_count = 256
#if subnet_count == 2:
#    subnet_cidr = 25
#    ip_count = 128
#if subnet_count == 3 or subnet_count == 4:
#    subnet_cidr = 26
#    ip_count = 64
#if subnet_count >= 5 and subnet_count <=8:
subnet_cidr = 27
ip_count = 32


#generate a 12 character password beginning with a capital letter and ending in a number
def passwd_generator(size=10, chars=string.ascii_letters + string.digits):
    first = random.choice(string.ascii_uppercase)
    last = random.choice(string.digits)
    middle = ''.join(random.choice(chars) for x in range(size))

    return first + middle + last


#cretate keypair
def create_keypair(team_name):
    keypair = boto3config.ec2client.create_key_pair(KeyName='%s' % (team_name))
    create_log(team_name, 'Private Key %s' % (team_name), keypair['KeyMaterial'])


#write log file
def create_log(team_name, desc, log):
    filename = "boto3/logs/%s-log.txt" % (team_name)
    file = open(filename,"a")
    file.writelines(desc)
    file.writelines(' - ')
    file.writelines(log)
    file.writelines('\n\n')
    file.close()
    print('Created %s' % (desc))


#create name, team, and event tags
def create_tags(resource, tag_name):
    tag = resource.create_tags(Tags=[
        {'Key': 'Name', 'Value': '%s' % (tag_name)},
        {'Key': 'Team', 'Value': '%s' % (tag_name)},
        {'Key': 'Event', 'Value': '%s' % (game.event)}
    ])
