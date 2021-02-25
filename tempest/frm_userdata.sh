#!/bin/bash 

sed -i 's/guest-file-open,//' /etc/sysconfig/qemu-ga
sed -i 's/guest-file-write,//' /etc/sysconfig/qemu-ga
sed -i 's/guest-file-read,//' /etc/sysconfig/qemu-ga
sed -i 's/guest-file-close,//' /etc/sysconfig/qemu-ga
sed -i '/SELINUX=enforcing/c SELINUX=disabled' /etc/selinux/config
echo "nameserver 8.8.8.8" >> /etc/resolv.conf
sleep 50
yum install python3 -y 
reboot
