#!/bin/bash 

DISTRO=$(awk '/ID=/' /etc/os-release | sed 's/ID=//' | sed -r 's/\"|\(|\)//g' | awk '{print $1;exit}')
if [[ "$DISTRO" == "rhel" || "$DISTRO" == "centos" ]]; then
    echo "rhel/centos based FRM image"
    sudo su
    NAME=$(awk '/^NAME=/' /etc/os-release | sed 's/NAME=//' | sed -r 's/\"|\(|\)//g')
    if grep -q "Stream" <<< "$NAME"
    then
	echo "centos8 stream image"
    else
	echo "centos8 image"
	sed -i 's/mirrorlist/#mirrorlist/g' /etc/yum.repos.d/CentOS-Linux-*
        sed -i 's|#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g' /etc/yum.repos.d/CentOS-Linux-*
    fi
    sed -i 's/guest-file-open,//' /etc/sysconfig/qemu-ga
    sed -i 's/guest-file-write,//' /etc/sysconfig/qemu-ga
    sed -i 's/guest-file-read,//' /etc/sysconfig/qemu-ga
    sed -i 's/guest-file-close,//' /etc/sysconfig/qemu-ga
    sed -i '/SELINUX=enforcing/c SELINUX=disabled' /etc/selinux/config
    echo "nameserver 8.8.8.8" > /etc/resolv.conf
    sleep 50
    yum install python3 lvm2 -y 
    reboot
else
    echo "ubuntu based FRM image"
fi
