''' boto3 vpc functions '''

from awsconfig import *
import os
import time

#create team subnets with appropriate cidr block for class c vpc based on number of subnets needed
def create_subnet(vpc, team_number, team_name, last_octet, subnet_name, avb_zone):
    subnet = vpc.create_subnet(CidrBlock='10.0.%s.%s/%s' % (team_number, last_octet, subnet_cidr), AvailabilityZone='%s%s' % (game.aws_region, avb_zone))
    subnet_tag_name = '%s-%s' % (team_name, subnet_name)
    tag = subnet.create_tags(Tags=[
        {'Key': 'Name', 'Value': '%s' % (subnet_tag_name)},
        {'Key': 'Team', 'Value': '%s' % (team_name)},
        {'Key': 'Event', 'Value': '%s' % (game.event)}
    ])
    create_log(team_name, 'Subnet %s-%s' % (team_name, subnet_name), subnet.id)

    return subnet


#create team vpc with cidr block 10.0.n.0/24 where n = team number
def create_vpc(team_number, team_name):
    vpc = boto3config.ec2resource.create_vpc(CidrBlock='10.0.%s.0/24' % (team_number))
    vpc.wait_until_available()
    create_tags(vpc, team_name)
    create_log(team_name, 'VPC %s' % (team_name), vpc.id)

    return vpc


#create and attach internet gateway
def create_ig(vpc, team_name):
    ig = boto3config.ec2resource.create_internet_gateway()
    vpc.attach_internet_gateway(InternetGatewayId=ig.id)
    create_tags(ig, team_name)
    create_log(team_name, 'Internet Gateway %s' % (team_name), ig.id)

    return ig


#create elastic ip
def create_elastic_ip(team_name):
    elastic_ip = boto3config.ec2client.allocate_address()
    #create tag for elastic ip - boto3 doesn't have a create_tags class for elastic ip
    os.system('aws ec2 create-tags --region %s --resources %s --tags Key=Name,Value="%s-NAT" Key=Team,Value="%s" Key=Event,Value="%s"' % (game.aws_region, elastic_ip['AllocationId'], team_name, team_name, game.event))
    filename = "%s-log.txt" % (team_name)
    file = open(filename,"a")
    file.writelines('\tElastic IP: %s\n' % (elastic_ip['PublicIp']))
    file.close()
    print('\tElastic IP: %s' % (elastic_ip['PublicIp']))

    elastic_ip = elastic_ip['AllocationId']

    return elastic_ip


#create nat gateway
def create_nat_gateway(elastic_ip, subnet, team_name):
    nat_gateway = boto3config.ec2client.create_nat_gateway(
        AllocationId = (elastic_ip),
        SubnetId = (subnet)
    )
    nat_gateway = nat_gateway['NatGateway']['NatGatewayId']
    os.system('aws ec2 create-tags --region %s --resources %s --tags Key=Name,Value="%s" Key=Team,Value="%s" Key=Event,Value="%s"' % (game.aws_region, nat_gateway, team_name, team_name, game.event))

    return nat_gateway


#request a peering connection to the interwebs vpc
def create_vpc_peering(vpc, team_name):
    vpc_peering = vpc.request_vpc_peering_connection(
        PeerVpcId=(game.interwebs_id)
    )
    #accept the peering request
    accept_peering_connection = boto3config.ec2resource.VpcPeeringConnection('interwebs_id')
    vpc_peering.wait_until_exists()
    vpc_peering.accept()
    #create tag for peering connection - boto3 doesn't have a create_tags class for vpc peering
    os.system('aws ec2 create-tags --region %s --resources %s --tags Key=Name,Value="%s" Key=Team,Value="%s" Key=Event,Value="%s"' % (game.aws_region, vpc_peering.id, team_name, team_name, game.event))
    create_log(team_name, 'Peering Connection %s' % (team_name), vpc_peering.id)

    return vpc_peering


#create a dhcp option set
def create_dhcp_set(vpc, team_number, team_name):
    instances = Instance.objects.filter(dns=True)
    for dns_server in instances:
        dhcp_set = boto3config.ec2client.create_dhcp_options(DhcpConfigurations=[
            { 'Key': 'domain-name-servers', 'Values': [ '10.0.%s.%s' % (team_number, dns_server.ip), ], },
            { 'Key': 'domain-name', 'Values': [ '%s' % (game.domain), ], }
            ])
    #associate dhcp set with vpc
    vpc.associate_dhcp_options(DhcpOptionsId=dhcp_set['DhcpOptions']['DhcpOptionsId'])
    os.system('aws ec2 create-tags --region %s --resources %s --tags Key=Name,Value="%s" Key=Team,Value="%s" Key=Event,Value="%s"' % (game.aws_region, dhcp_set['DhcpOptions']['DhcpOptionsId'], team_name, team_name, game.event))
    create_log(team_name, 'DHCP Option Set %s' % (team_name), dhcp_set['DhcpOptions']['DhcpOptionsId'])


#add a route to a route table
def add_route(rtb, destination, cidr):
    route = boto3config.ec2resource.RouteTable('%s' % (rtb))
    route.create_route(
        DestinationCidrBlock=(cidr),
        VpcPeeringConnectionId=(destination.id)
    )

def add_route_nat(rtb, destination, cidr):
    route = boto3config.ec2resource.RouteTable('%s' % (rtb))
    route.create_route(
        DestinationCidrBlock=(cidr),
        NatGatewayId=(destination)
    )


#associate route table
def associate_route_table(route_table, subnet):
    associate_rt = boto3config.ec2client.associate_route_table(
        RouteTableId = (route_table),
        SubnetId = (subnet.id)
    )


#get the route table id for the route table attached to the created vpc
def create_vpc_route_table(vpc, vpc_peering, ig, team_name):
    vpc_route_table = vpc.route_tables.all()
    for t in vpc_route_table:
        vpc_route_table_id = t.route_table_id
    #add route to vpc peering connection for interwebs traffic
    route = boto3config.ec2resource.RouteTable('%s' % (vpc_route_table_id))
    route.create_route(
        DestinationCidrBlock=(game.interwebs_cidr),
        VpcPeeringConnectionId=(vpc_peering.id)
    )
    #add default route to internet gateway
    route.create_route(
        DestinationCidrBlock='0.0.0.0/0',
        GatewayId=(ig.id)
    )
    create_tags(route, team_name)
    create_log(team_name, 'Route Table %s' % (team_name), vpc_route_table_id)


#create route table for team subnets attached to nat gateway
def create_nat_gateway_route_table(vpc, team_name, nat_gateway, vpc_peering):
    nat_gateway_route_table = boto3config.ec2resource.create_route_table(
        VpcId = (vpc)
    )
    tagname = '%s-NAT' % (team_name)
    create_tags(nat_gateway_route_table, tagname)
    create_log(team_name, 'Route Table %s-Nat' % (team_name), nat_gateway_route_table.id)
    print('Waiting for Nat Gateway to become available')
    time.sleep(10) #wait for nat gateway
    add_route_nat(nat_gateway_route_table.id, nat_gateway, '0.0.0.0/0') #add default route to nat gateway
    add_route(nat_gateway_route_table.id, vpc_peering, '172.31.0.0/16') #add route to interwebs

    return nat_gateway_route_table.id
