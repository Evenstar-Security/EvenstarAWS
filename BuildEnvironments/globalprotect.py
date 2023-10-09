import requests
import boto3
import paramiko
import time

#Step 1 - Build security group which only allows SSH and HTTPS from this IP
ip_response = requests.get("http://ipinfo.io/ip")
my_ip = ip_response.text
print(my_ip)