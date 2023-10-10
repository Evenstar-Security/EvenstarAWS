import requests
import boto3
import paramiko
import time
import json
from pathlib import Path
from pythonping import ping
from io import StringIO

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
                            'Description': 'Allow ICMP from my IP'
                        },
                    ],
                    'FromPort': -1,
                    'ToPort': -1
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

    #Step 4 - Launch N NGFWs with ami-0efe54d5b2db9e6da
    def palos(N: int, security_group_id: str, key_name: str):
        ec2_client = session.client('ec2')
        responses = []
        for i in range(1,N+1):
            create_response = ec2_client.run_instances(
                BlockDeviceMappings=[
                    {
                        'Ebs': {
                            'DeleteOnTermination': True,
                            'VolumeSize': 60,
                            'VolumeType': 'standard',
                        },
                        'NoDevice': 'string'
                    },
                ],
                ImageId = "ami-0efe54d5b2db9e6da",
                InstanceType = "m4.large",
                KeyName = key_name,
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
                        'PrivateIpAddress': sysinfo['subnet']+str(i*2+2),
                        'SubnetId': sysinfo['subnet_id'],
                    }
                ]
            )
            con = True
            while con:
                try:
                    instance_response = ec2_client.describe_instances(
                        InstanceIds = [
                            create_response['Instances'][0]['InstanceId']
                        ]
                    )
                    if 'PublicIpAddress' in instance_response['Reservations'][0]['Instances'][0]:
                        print("Instance",i,"has IP",instance_response['Reservations'][0]['Instances'][0]['PublicIpAddress'])
                        responses.append(instance_response['Reservations'][0])
                        con = False
                    else:
                        print("Public IP not yet available for instance",i)
                        time.sleep(10)
                except:
                    print("Can't describe instance yet")
                    time.sleep(10)
        return responses
    
    #Step 5 Add Data Interface
    def interfaces(instance_ids: list):
        #Create and attach the external interface
        ec2_client = session.client('ec2')
        for i in range(len(instance_ids)):
            student_num = i+1
            interface_response = ec2_client.create_network_interface(
                Description='Student '+str(student_num+1)+' Internet Interface',
                DryRun=False,
                Groups=[
                    sysinfo["group"]
                ],
                PrivateIpAddress=sysinfo['ext_subnet']+str(student_num*2+3),
                SubnetId=sysinfo["subnet_id"],
                EnablePrimaryIpv6=False
            )

            print("Interface created with ID "+interface_response['NetworkInterface']['NetworkInterfaceId'])

            con = True
            while con:
                try:
                    attach_response = ec2_client.attach_network_interface(
                        DeviceIndex=1,
                        DryRun=False,
                        InstanceId=instance_ids[i],
                        NetworkInterfaceId=interface_response['NetworkInterface']['NetworkInterfaceId']
                    )
                    con = False
                except:
                    print("Not running yet")
                    time.sleep(10)

            print("External data interface attached to instance", instance_ids[i])
    
class configure():    
    #Step 1 - Configure web server
    def web_server():
        return 0

    #Step 2 - Set initial palo configuration: admin pw, interface swap, http mgmt
    def palos(ips: list, admin_password: str, key_string: str):
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
        for ip in ips:
            con = True
            while con:
                my_ping = ping(ip,verbose=True,count=1)
                if "Request timed out" in str(my_ping):
                    print("Can't ping",ip,"yet")
                    time.sleep(10)
                else:
                    print("Ping successful")
                    con = False
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            not_really_a_file = StringIO(key_string)
            pkey = paramiko.RSAKey.from_private_key(not_really_a_file)
            not_really_a_file.close()
            con = True
            while con:
                try:
                    ssh.connect(ip,username="admin",pkey=pkey)
                    print("SSH successfully connected")
                    con = False
                except Exception as error:
                    print("Can't connect to SSH yet")
                    print(error)
                    time.sleep(10)
        return 0
    
    #Step 3 - Adjust network interface configurations on Palo EC2 instance
    def interfaces(network_interface_id: str):
        ec2_client = session.client('ec2')
        modify_response = ec2_client.modify_network_interface_attribute(
            NetworkInterfaceId = network_interface_id,
            SourceDestCheck={ 'Value': False }
        )

        return modify_response

class destroy():

    #Step 1 - Terminate Palos
    def palos(instance_ids: list):
        ec2_client = session.client('ec2')
        response = ec2_client.terminate_instances(
            InstanceIds=instance_ids
        )
        return response
    
    #Step 2 - Delete leftover network interface
    def interfaces():
        return 0
    
    #Step 3 - Terminate web server
    def web_server():
        return 0
    
    #Step 4 - Delete security group
    def security_group(group_id: str):
        ec2_client = session.client('ec2')
        response = ec2_client.delete_security_group(
            GroupId=group_id,
        )
        return response
    
    #Step 5 - Delete key pair
    def key_pair(key_pair_id: str):
        ec2_client = session.client('ec2')
        response = ec2_client.delete_key_pair(
            KeyPairId=key_pair_id
        )
        return response

#Run the steps in proper order
def main():
    #Security Group
    security_group = build.security_group()
    print("Security Group ID:",security_group['GroupId'])

    #Key Pair
    key_pair = build.key_pair()
    print("The key is",key_pair['KeyMaterial'])

    #Palo EC2 Instances
    palos = build.palos(N=1, security_group_id=security_group['GroupId'], key_name=key_pair['KeyName'])
    print("InstanceID:",palos[0]['Instances'][0]['InstanceId'])

    #Build List of IPs
    ips = []
    for i in range(len(palos)):
        ips.append(palos[i]['Instances'][0]['PublicIpAddress'])

    #Build List of Instance IDs
    instance_ids = []
    for i in range(len(palos)):
        instance_ids.append(palos[i]['Instances'][0]['InstanceId'])  

    #Configure Palo
    configure.palos(ips=ips,admin_password=sysinfo['admin_password'],key_string=key_pair['KeyMaterial'])  

    #Create and attach additional network interface

    #Configure network interfaces


    #Destroy everything
    destroy.palos(instance_ids=instance_ids)
    destroy.security_group(security_group['GroupId'])
    destroy.key_pair(key_pair_id=key_pair['KeyPairId'])
    return 0

main()