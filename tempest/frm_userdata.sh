#!/bin/bash 

DISTRO=$(awk '/ID=/' /etc/os-release | sed 's/ID=//' | sed -r 's/\"|\(|\)//g' | awk '{print $1;exit}')
if [[ "$DISTRO" == "rhel" || "$DISTRO" == "centos" ]]; then
    echo "rhel/centos based FRM image"
    sed -i 's/guest-file-open,//' /etc/sysconfig/qemu-ga
    sed -i 's/guest-file-write,//' /etc/sysconfig/qemu-ga
    sed -i 's/guest-file-read,//' /etc/sysconfig/qemu-ga
    sed -i 's/guest-file-close,//' /etc/sysconfig/qemu-ga
    sed -i '/SELINUX=enforcing/c SELINUX=disabled' /etc/selinux/config
    echo "nameserver 8.8.8.8" >> /etc/resolv.conf
    sleep 50
    yum install python3 lvm2 -y 
    reboot
else
    echo "ubuntu based FRM image"
fi
