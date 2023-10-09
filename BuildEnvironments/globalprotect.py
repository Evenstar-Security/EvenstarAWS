import requests
import boto3
import paramiko
import time
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

with open("../../sysinfo/globalprotect.json","r") as f:
    sysinfo = json.load(f)

session = boto3.Session(
    aws_access_key_id=sysinfo["aws_access_key_id"],
    aws_secret_access_key=sysinfo["aws_secret_access_key"],
    region_name=sysinfo["region_name"]
)

class build():

    #Step 1 - Build security group which only allows SSH and HTTPS from this IP
    def security_group():
        #Get my IP
        ip_response = requests.get("http://ipinfo.io/ip")
        my_ip = ip_response.text

        #Create the security group
        ec2_client = session.client('ec2')
        security_group = ec2_client.create_security_group(
            Description='Allow HTTPS, SSH, and ICMP only from my IP and all internal traffic',
            GroupName='MyIpOnly',
            VpcId=sysinfo['vpc_id'],
        )
        ingress_response = ec2_client.authorize_security_group_ingress(
            GroupId=security_group['GroupId'],
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'IpRanges': [
                        {
                            'CidrIp': my_ip+"/32",
                            'Description': 'Allow SSH from my IP'
                        },
                    ],
                    'FromPort': 22,
                    'ToPort': 22
                },
                {
                    'IpProtocol': 'tcp',
                    'IpRanges': [
                        {
                            'CidrIp': my_ip+"/32",
                            'Description': 'Allow HTTPS from my IP'
                        },
                    ],
                    'FromPort': 443,
                    'ToPort': 443
                },
                                {
                    'IpProtocol': 'icmp',
                    'IpRanges': [
                        {
                            'CidrIp': my_ip+"/32",
                            'Description': 'Allow HTTPS from my IP'
                        },
                    ],
                    'FromPort': 443,
                    'ToPort': 443
                },
                {
                    'IpProtocol': '-1',
                    'IpRanges': [
                        {
                            'CidrIp': "10.0.0.0/16",
                            'Description': 'Allow all internal traffic'
                        },
                    ],
                    'FromPort': -1,
                    'ToPort': -1
                }
            ]
        )
        return security_group
    
    #Step 2 - Create a Key Pair for this project
    def key_pair():
        ec2_client = session.client('ec2')
        current_time = str(int(time.time()))
        response = ec2_client.create_key_pair(
            KeyName=current_time,
            KeyType='rsa',
            KeyFormat='pem'
        )
        return response

    #Step 3 - Launch RHEL Web Server ami-026ebd4cfe2c043b2
    def web_server():
        return 0
    
    #Step 4 - Configure NGINX on Web Server
    def configure_nginx():
        return 0

    #Step 5 - Launch N NGFWs with ami-0efe54d5b2db9e6da
    def palos(N: int, security_group_id: str):
        ec2_client = session.client('ec2')
        responses = []
        for i in range(1,N+1):
            instance_response = ec2_client.run_instances(
                ImageId = "ami-0efe54d5b2db9e6da",
                InstanceType = "m4.large",
                MinCount = 1,
                MaxCount = 1,
                NetworkInterfaces=[
                    {
                        'AssociatePublicIpAddress': True,
                        'DeleteOnTermination': True,
                        'DeviceIndex': 0,
                        'Groups': [
                            security_group_id
                        ],
                        'PrivateIpAddress': sysinfo['subnet']+str(i+7),
                        'SubnetId': sysinfo['subnet_id'],
                    }
                ]
            )
            responses.append(instance_response)
        return responses
    
    #Step 6 - Set initial palo configuration: admin pw, interface swap, http mgmt
    def configure_palos(ips: list, admin_password: str):
        commands = [
            'configure\n',
            #Set admin password for logging in
            'set mgt-config users admin password\n',
            admin_password+"\n",
            admin_password+"\n",
            #Set http management
            'set deviceconfig system service disable-http no\n'
            'commit\n',
            'exit\n',

            #Swap management interface
            'set system setting mgmt-interface-swap enable yes\n',
            'y',

            #Restart system
            'request restart system\n',
            'y',
        ]
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        pkey = paramiko.RSAKey.from_private_key(StringIO.StringIO(sysinfo["ssh_key"]))
        return 0
    
    #Step 7 - Adjust network interface configurations on Palo EC2 instance
    def network_interfaces(network_interface_id: str):
        ec2_client = session.client('ec2')
        modify_response = ec2_client.modify_network_interface_attribute(
            NetworkInterfaceId = network_interface_id,
            SourceDestCheck={ 'Value': False }
        )
        return modify_response

class destroy():

    #Step 1 - Terminate Palos
    def palos():
        return 0
    
    #Step 2 - Delete leftover network interfaces
    def delete_interfaces():
        return 0
    
    #Step 3 - Terminate web server
    def terminate_web_server():
        return 0
    
    #Step 4 - Delete security group
    def security_group(group_id: str):
        ec2_client = session.client('ec2')
        ec2_client.delete_security_group(
            GroupId=group_id,
        )
        return 0
    
    #Step 5 - Delete key pair
    def key_pair(key_pair_id: str):
        ec2_client = session.client('ec2')
        response = ec2_client.delete_key_pair(
            KeyPairId=key_pair_id
        )
        return 0

#Run the steps in proper order
def main():
    #Security Group
    security_group = build.security_group()
    print("Security Group ID:",security_group['GroupId'])

    #Key Pair
    key_pair = build.key_pair()
    print("The key is",key_pair['KeyMaterial'])


    #palos = build.launch_palos(N=1, security_group_id=security_group['GroupId'])
    #print("InstanceID:",palos[0]['Instances'][0]['InstanceId'])
    
    #Destroy
    destroy.security_group(security_group['GroupId'])
    destroy.key_pair(key_pair_id=key_pair['KeyPairId'])
    return 0

main()