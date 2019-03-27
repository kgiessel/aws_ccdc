''' boto3 workspaces functions '''

from awsconfig import *

def create_directory(team_name, vpc, workspaces1_id, workspaces2_id):
    #create a simple ad directory for aws workspaces
    directory_passwd = passwd_generator()
    ds = boto3.client('ds')
    directory = ds.create_directory(
        Name='ws.%s.%s' % (team_name, game.domain),
        ShortName=(team_name),
        Password=(directory_passwd),
        Description=(team_name),
        Size='Small',
        VpcSettings={
            'VpcId': (vpc.id),
            'SubnetIds': [
                (workspaces1_id),
                (workspaces2_id),
            ]
        }
    )
    create_log(team_name, 'Workspace Directory ws.%s.%s' % (team_name, game.domain), directory['DirectoryId'])
    create_log(team_name, 'Directory Password', directory_passwd)

    return directory
