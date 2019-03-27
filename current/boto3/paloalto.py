''' create palo alto firewall '''

from awsconfig import *

#create palo alto subnet
def create_pan_subnet():
    vpc = boto3config.ec2resource.Vpc(game.interwebs_id)
    subnet = vpc.create_subnet(CidrBlock='172.31.20.0/24', AvailabilityZone='%sa' % (game.aws_region))
    tag = subnet.create_tags(Tags=[
        {'Key': 'Name', 'Value': '%s' % ('PAN')},
        {'Key': 'Team', 'Value': '%s' % ('Blackteam')},
        {'Key': 'Event', 'Value': '%s' % (game.event)}
    ])
    create_log('Blackteam', 'Subnet PAN', subnet.id)

    return pan_subnet


#create team Palo Alto PA-100
def create_pan():
    def create_instance(team_name, team_number, subnet_id, instance, security_group):
        pan_instance = boto3config.ec2resource.create_instances(
            ImageId=(''),
            InstanceType=(instance.type),
            KeyName=(team_name),
            SecurityGroupIds=[(security_group.id)],
            SubnetId=(subnet_id),
            PrivateIpAddress='10.0.%s.%s' % (team_number, instance.ip),
            MaxCount=1,
            MinCount=1
        )
        for t in pan_instance:
            instance_id = t.instance_id
        pan_instance = boto3config.ec2resource.Instance(instance_id)
