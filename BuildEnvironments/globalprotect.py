import requests
import boto3
import paramiko
import time
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class build():
    with open("../../sysinfo/globalprotect.json","r") as f:
        sysinfo = json.load(f)

    session = boto3.Session(
        aws_access_key_id=sysinfo["aws_access_key_id"],
        aws_secret_access_key=sysinfo["aws_secret_access_key"],
        region_name=sysinfo["region_name"]
    )
    #Step 1 - Build security group which only allows SSH and HTTPS from this IP
    def security_group():
        ip_response = requests.get("http://ipinfo.io/ip")
        my_ip = ip_response.text
        print(my_ip)
        return 0

    #Step 2 - Launch Web Server which can only be accessed within subnet
    def web_server():
        return 0

    #Step 3 - Launch N NGFWs with ami-0efe54d5b2db9e6da
    def launch_palos(N, ):
        return 0
    
    #Step 4 - Set initial palo configuration: admin pw, interface swap, http mgmt
    def configure_palos():
        return 0
    
    #Step 5 - Adjust network interface configurations on palo
    def network_interfaces():
        return 0
    


class destroy():
    def nada():
        return 0

#Run the steps in proper order
def main():
    build.launch_palos(N=1)
    print(BASE_DIR)
    return 0

main()