"""shutdown-ec2.py"""

__author__ = "Kurt Giessel"
__copyright__ = "Copyright 2019, Highline College"
__license__ = "GPL"
__version__ = "0.1"
__email__ = "kgiessel@highline.edu"

import boto3
import configparser
import MySQLdb
import sys
import time

config = configparser.ConfigParser()
config.read('config.ini')

#database config
db = MySQLdb.connect('localhost','django','########','django')

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

#functions

def stop_team_instances(team_name):
    filters = [{'Name':'tag:Team', 'Values':[(team_name)]}]
    team_instances = list(gbl_ec2resource.instances.filter(Filters=filters))
    for t in team_instances:
        instance_id = t.instance_id
        instance = gbl_ec2resource.Instance(instance_id)
        state = instance.state['Name']
        if state == "running":
            print("shutting down %s instance %s" % (team_name, instance_id))
            #stop = instance.stop()
        else:
            print("%s instance %s is %s" % (team_name, instance_id, state))


def get_game_status(team_name):
    cursor = db.cursor()
    sql = "SELECT starttime FROM portal_teaminfo WHERE team = '%s'" % (team_name)
    cursor.execute(sql)
    starttime = cursor.fetchone()
    starttime = int(starttime[0])
    if starttime == 0:
        print("Game has not started for %s" % (team_name))
    else:
        now = time.time()
        endtime = starttime + 14400
        if now > endtime:
            print("Game has ended for %s" % (team_name))
            stop_team_instances(team_name.title())
        else:
            print("game is still running")


#main

team_number = 0
while team_number <= int(num_teams):
    if team_number < 10:
        team_name = '%s0%s' % (name_teams, team_number)
    else:
        team_name = '%s%s' % (name_teams, team_number)

    get_game_status(team_name)

    team_number += 1
