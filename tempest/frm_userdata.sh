#!/bin/bash

DISTRO=$(awk '/ID=/' /etc/os-release | sed 's/ID=//' | sed -r 's/\"|\(|\)//g' | awk '{print $1;exit}')
if [[ "$DISTRO" == "rhel" || "$DISTRO" == "centos" ]]; then
    echo "rhel/centos based FRM image"
    sudo su
    NAME=$(awk '/^NAME=/' /etc/os-release | sed 's/NAME=//' | sed -r 's/\"|\(|\)//g')
    if grep -q "Stream" <<< "$NAME"
    then
	    echo "centos8 stream image"
    elif grep -q "Red Hat" <<< "$NAME"
    then
	    echo "Redhat image"
	    echo "enabling subscription manager"
	    REDHAT_USERNAME=sampleusername
	    REDHAT_PWD=samplepassword
	    echo "nameserver 8.8.8.8" > /etc/resolv.conf
	    subscription-manager register --username=$REDHAT_USERNAME --password=$REDHAT_PWD --insecure
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
    sudo su
    echo "nameserver 8.8.8.8" > /etc/resolv.conf
    sleep 10
    apt-get update
    apt-get install qemu-guest-agent -y
    systemctl enable qemu-guest-agent
    NAME=$(awk '/^PRETTY_NAME=/' /etc/os-release | sed 's/PRETTY_NAME=//' | sed -r 's/\"|\(|\)//g')
    if grep -q "Ubuntu 18.04" <<< "$NAME"
    then
	    echo "Ubuntu 18.04 image"
	    sed -i '/DAEMON_ARGS=/c DAEMON_ARGS="-F/etc/qemu/fsfreeze-hook"' /etc/init.d/qemu-guest-agent
    else
	    echo "Ubuntu 20.04/22.04 image"
	    mkdir -p /etc/systemd/system/qemu-guest-agent.service.d
	    echo -e "[Service]\nExecStart=\nExecStart=/usr/sbin/qemu-ga -F/etc/qemu/fsfreeze-hook" >> /etc/systemd/system/qemu-guest-agent.service.d/override.conf
    fi
    systemctl daemon-reload
    systemctl restart qemu-guest-agent
    apt-get install python3
    reboot
fi
