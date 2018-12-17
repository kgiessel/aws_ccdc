#!/usr/bin/python3

"""comp-up.py: Spin up servers, security groups in AWS."""

__author__ = "Kurt Giessel"
__copyright__ = "Copyright 2018, Highline College"
__license__ = "GPL"
__version__ = "0.1"
__email__ = "kgiessel@highline.edu"

import os
from subprocess import PIPE, run
import time
import configparser
config = configparser.ConfigParser()
config.read('config.ini')

##########
#variables

event = (config.items('EVENT'))
eventID = event[0][1]
teams = (config.items('TEAMS'))
numTeams = teams[0][1]
teamName = teams[1][1]
servers = (config.items('SERVERS'))
network = (config.items('NETWORK'))
vpc = network[0][1]
cidr = network[1][1]
team = 1

##########
#functions

def get_stdout(cmd):
    result = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    return result.stdout

#####
#main

while team <= int(numTeams):

    if team < 10:
        teamNum = '0%s' % team
    else:
        teamNum = team
    teamNameNum = teamName + str(teamNum)

    print('')
    print('###################################')
    print('')
    print('Starting Config for %s' % (teamNameNum))
    print('')
    print('###################################')
    print('')

    #create subnet
    subnetID = get_stdout('aws ec2 create-subnet --vpc-id %s --cidr-block 192.168.%s.0/%s' % (vpc, str(team), str(cidr))) #create subnet
    subnetID = subnetID.splitlines()[9]
    subnetID = subnetID.split()[1][1:-2] #get subnetID
    os.system('aws ec2 create-tags --resources %s --tags Key=Name,Value="%s" Key=Team,Value="%s" Key=Event,Value="%s"' % (subnetID, teamNameNum, teamNameNum, eventID)) #apply tag to subnet

    for server in range(len(servers)):

        instanceName = teamNameNum + '-' + servers[server][0] #instance name TeamNameXX-Server
        imageID = servers[server][1].split()[1] #AMI image used
        ipAddr = '192.168.' + str(team) + '.' + servers[server][1].split()[0] #IP Address -

        print('')
        print('### Creating %s ###' % (instanceName))
        print('')

        #create security group
        print('Creating Security Group %s' % (instanceName))
        secGroup = get_stdout('aws ec2 create-security-group --vpc-id %s --group-name %s --description "%s Created by comp-up.py"' % (vpc, instanceName, instanceName)) #create security group
        secGroup = secGroup.splitlines()[1]
        secGroup = secGroup.split()[1][1:-1] #get security group name
        print('Security Group %s created with id %s' % (instanceName, secGroup))
        os.system('aws ec2 authorize-security-group-ingress --group-id %s --protocol tcp --port 0-65535 --cidr 192.168.0.0/16' % (secGroup)) #add rules to security group
        os.system('aws ec2 authorize-security-group-ingress --group-id %s --protocol udp --port 0-65535 --cidr 192.168.0.0/16' % (secGroup)) #add rules to security group
        print('Opened all TCP and UDP ports on rule %s' % (secGroup))

        #get platform to set remote security group
        platform = get_stdout('aws ec2 describe-images --image-ids %s --query Images[*].{OS:Platform} --output text' % (imageID)) #get platform
        if platform.rstrip() == 'windows':
            remoteSG = network[2][1]
            instanceType = 't2.medium'
        else:
            remoteSG = network[3][1]
            instanceType = 't2.micro'

        #create instance
        print('Creating %s from image %s with IP %s on subnet %s with security groups %s and %s' % (instanceName, imageID, ipAddr, subnetID, secGroup, remoteSG))
        null = get_stdout('aws ec2 run-instances --image-id %s --count 1 --instance-type %s --key-name blueteam --security-group-ids %s %s --subnet-id %s --private-ip-address %s --associate-public-ip-address' % (imageID, instanceType, secGroup, remoteSG, subnetID, ipAddr)) #create instance

        time.sleep(5)
        instanceID = get_stdout('aws ec2 describe-instances --filters "Name=network-interface.addresses.private-ip-address,Values=%s" --query Reservations[*].Instances[*].[InstanceId] --output text' % (ipAddr))
        instanceID = instanceID.rstrip()
        while not instanceID:
            time.sleep(5)
            instanceID = get_stdout('aws ec2 describe-instances --filters "Name=network-interface.addresses.private-ip-address,Values=%s" --query Reservations[*].Instances[*].[InstanceId] --output text' % (ipAddr))
        #allocate Elastic IP
        print('Allocating Elastic IP and associating it with %s' % (instanceID))
        allocationID = get_stdout('aws ec2 allocate-address --domain vpc') #allocate elastic IP
        allocationID = allocationID.splitlines()[3]
        allocationID = allocationID.split()[1][1:-1]
        instanceState = get_stdout('aws ec2 describe-instance-status --instance-id %s --query InstanceStatuses[*].{Status:InstanceState} --output text' % (instanceID))
        while not instanceState: #wait for instance state running before associating elastic IP
            time.sleep(5)
            instanceState = get_stdout('aws ec2 describe-instance-status --instance-id %s --query InstanceStatuses[*].{Status:InstanceState} --output text' % (instanceID))
        get_stdout('aws ec2 associate-address --instance-id %s --allocation-id %s' % (instanceID, allocationID)) #associate instance and elastic IP

        #create tags
        print('Creating Tags for InstanceID %s, AllocationID %s, and SecurityGroupID %s with values %s, %s, %s' % (instanceID, allocationID, secGroup, instanceName, teamNameNum, eventID))
        os.system('aws ec2 create-tags --resources %s %s %s --tags Key=Name,Value="%s" Key=Team,Value="%s" Key=Event,Value="%s"' % (instanceID, allocationID, secGroup, instanceName, teamNameNum, eventID)) #add tags

    team += 1

print('###################################')
print('')
print('%s Successfully Created' % (numTeams))
print('')
print('###################################')
