
import paramiko
import time
def SshRemoteMachineConnectionWithRSAKey(ipAddress):
    username = "ubuntu"
    key_file = "/root/tempest/etc/mykeypair.pem"
    ssh=paramiko.SSHClient()
    k = paramiko.RSAKey.from_private_key_file(key_file)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.load_system_host_keys()
    ssh.connect(hostname=ipAddress, username=username ,pkey=k)
    return ssh


def calculatemmd5checksum(clientIP, dirPath):
    try:
        local_md5sum = ""
        ssh = SshRemoteMachineConnectionWithRSAKey(clientIP)
        buildCommand = "sudo find " + str(dirPath) + """/ -type f -exec md5sum {} +"""
        stdin, stdout, stderr = ssh.exec_command(buildCommand)
        time.sleep(10)
        for line in  stdout.readlines():
            local_md5sum += str(line.split(" ")[0])
        print local_md5sum
    except Exception as e:
        print("Exception: " + str(e))


calculatemmd5checksum("192.168.1.26", "mount_data_b/")
