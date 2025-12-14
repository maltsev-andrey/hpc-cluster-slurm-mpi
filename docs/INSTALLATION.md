# Installation Guide

## Overview

This document provides step-by-step instructions for installing and configuring the SLURM on HPC cluster. The installation process accounts for the air-gapped nature of the compute nodes, using an NFS-based offline package repository.

## Prerequisites

Before beginning the installation, ensure the following requirements are met:

### Hardware Requirements

1. One head node with connectivity to both external and internal networks
2. Four compute nodes connected to the internal network only
3. Shared storage accessible via NFS from all nodes
4. Minimum 8 GB RAM per node
5. Minimum 4 CPU cores per node (12 recommended)

### Software Requirements

1. Red Hat Enterprise Linux 9.x installed on all nodes
2. Network connectivity configured on all nodes
3. NFS share mounted at /nfs/shared on all nodes
4. SSH key-based authentication from head node to all compute nodes
5. Ansible installed on the head node

### Network Requirements

1. Head node external IP: 170.168.1.30
2. Head node internal IP: 10.10.10.1
3. Compute node IPs: 10.10.10.11-14
4. All nodes can resolve hostnames via /etc/hosts

## Installation Steps

### Step 1: Configure Host Resolution

On all nodes, add the following entries to /etc/hosts:

```
10.10.10.1      srv-hpc-01 hpc-head
10.10.10.11     srv-hpc-02 hpc-compute-01
10.10.10.12     srv-hpc-03 hpc-compute-02
10.10.10.13     srv-hpc-04 hpc-compute-03
10.10.10.14     srv-hpc-05 hpc-compute-04
```

Verify connectivity from the head node:

```bash
for i in 02 03 04 05; do
    ssh srv-hpc-$i hostname
done
```

### Step 2: Set Up SSH Key Authentication

On the head node, generate an SSH key pair if not already present:

```bash
ssh-keygen -t rsa -N ""
```

Copy the public key to all compute nodes:

```bash
ssh-copy-id srv-hpc-02
ssh-copy-id srv-hpc-03
ssh-copy-id srv-hpc-04
ssh-copy-id srv-hpc-05
```

Verify passwordless SSH access:

```bash
ssh srv-hpc-02 "echo 'SSH working'"
```

### Step 3: Install Ansible

On the head node, install Ansible:

```bash
sudo dnf install ansible -y
```

Verify the installation:

```bash
ansible --version
```

### Step 4: Create Ansible Inventory

Create the inventory file at /home/ansible/slurm-ansible/inventory.ini:

```ini
[head]
srv-hpc-01 ansible_host=10.10.10.1

[compute]
srv-hpc-02 ansible_host=10.10.10.11
srv-hpc-03 ansible_host=10.10.10.12
srv-hpc-04 ansible_host=10.10.10.13
srv-hpc-05 ansible_host=10.10.10.14

[all:vars]
ansible_user=ansible
ansible_become=yes
local_repo_path=/nfs/shared/slurm-repo
```

Test connectivity to all nodes:

```bash
ansible -i inventory.ini all -m ping
```

Expected output shows SUCCESS for each node.

### Step 5: Download Packages to NFS Share

On the head node (which has internet access), download all required packages:

```bash
# Set repository directory
REPO_DIR="/nfs/shared/slurm-repo"

# Create directory
sudo mkdir -p $REPO_DIR

# Install repository tools
sudo dnf install -y epel-release
sudo dnf install -y createrepo dnf-plugins-core

# Download base dependencies
dnf download --resolve --destdir=$REPO_DIR \
    readline lua lua-libs ncurses ncurses-libs ncurses-base

# Download MUNGE packages
dnf download --resolve --destdir=$REPO_DIR \
    munge munge-libs munge-devel

# Download SLURM packages with all dependencies
dnf download --resolve --alldeps --destdir=$REPO_DIR \
    slurm slurm-libs slurm-slurmd slurm-slurmctld slurm-perlapi

# Download s-nail (provides /bin/mailx required by SLURM)
dnf download --resolve --destdir=$REPO_DIR s-nail

# Download additional dependencies
dnf download --resolve --destdir=$REPO_DIR \
    libjwt freeipmi hwloc lz4 http-parser json-c pmix

# Create repository metadata
createrepo $REPO_DIR

# Set permissions
chmod -R 755 $REPO_DIR
```

Verify the repository contains packages:

```bash
ls /nfs/shared/slurm-repo/*.rpm | wc -l
```

The count should be approximately 30 packages.

### Step 6: Create SLURM Configuration Template

Create the template file at templates/slurm.conf.j2:

```
# slurm.conf - SLURM configuration file

# Cluster Identity
ClusterName=hpc-cluster
SlurmctldHost=srv-hpc-01

# Authentication
AuthType=auth/munge
CryptoType=crypto/munge

# Ports
SlurmctldPort=6817
SlurmdPort=6818

# Paths and Directories
SlurmdSpoolDir=/var/spool/slurm/d
StateSaveLocation=/var/spool/slurm/ctld
SlurmctldPidFile=/run/slurmctld.pid
SlurmdPidFile=/run/slurmd.pid

# Logging
SlurmctldLogFile=/var/log/slurm/slurmctld.log
SlurmdLogFile=/var/log/slurm/slurmd.log
SlurmctldDebug=info
SlurmdDebug=info

# Process Tracking
ProctrackType=proctrack/linuxproc
ReturnToService=2

# Scheduling
SchedulerType=sched/backfill
SelectType=select/cons_tres
SelectTypeParameters=CR_Core

# Timeouts
SlurmctldTimeout=120
SlurmdTimeout=300
InactiveLimit=0
MinJobAge=300
KillWait=30
Waittime=0

# MPI Configuration
MpiDefault=pmix

# Compute Nodes Definition
NodeName=srv-hpc-02 CPUs=12 RealMemory=7600 State=UNKNOWN
NodeName=srv-hpc-03 CPUs=12 RealMemory=7600 State=UNKNOWN
NodeName=srv-hpc-04 CPUs=12 RealMemory=7600 State=UNKNOWN
NodeName=srv-hpc-05 CPUs=12 RealMemory=7600 State=UNKNOWN

# Partition Definition
PartitionName=compute Nodes=srv-hpc-[02-05] Default=YES MaxTime=INFINITE State=UP
```

Important: The RealMemory value (7600) must be less than or equal to the actual available memory on compute nodes. Use the free -m command to check available memory and set RealMemory approximately 400 MB below the total.

### Step 7: Create Ansible Playbook

Create the main playbook at slurm_install_offline.yml:

```yaml
---
# SLURM Offline Installation Playbook

# Configure local repository on all nodes
- name: Configure local repository on all nodes
  hosts: all
  become: yes
  vars:
    local_repo_path: /nfs/shared/slurm-repo

  tasks:
    - name: Create local SLURM repo file
      copy:
        dest: /etc/yum.repos.d/slurm-local.repo
        content: |
          [slurm-local]
          name=SLURM Local Repository
          baseurl=file://{{ local_repo_path }}
          enabled=1
          gpgcheck=0
          priority=1
        mode: '0644'

    - name: Clean DNF cache
      command: dnf clean all
      changed_when: false

# Create SLURM user and group
- name: Setup SLURM user on all nodes
  hosts: all
  become: yes

  tasks:
    - name: Create slurm group
      group:
        name: slurm
        system: yes
        state: present

    - name: Create slurm user
      user:
        name: slurm
        group: slurm
        system: yes
        home: /var/lib/slurm
        shell: /sbin/nologin
        create_home: no
        state: present

# Install packages
- name: Install MUNGE on all nodes
  hosts: all
  become: yes

  tasks:
    - name: Install MUNGE packages
      dnf:
        name:
          - munge
          - munge-libs
        state: present
        disablerepo: "*"
        enablerepo: "slurm-local"

- name: Install SLURM on all nodes
  hosts: all
  become: yes

  tasks:
    - name: Install SLURM base packages
      dnf:
        name:
          - slurm
          - slurm-libs
          - slurm-slurmd
        state: present
        disablerepo: "*"
        enablerepo: "slurm-local"

- name: Install SLURM controller on head node
  hosts: head
  become: yes

  tasks:
    - name: Install SLURM controller packages
      dnf:
        name:
          - slurm-slurmctld
          - slurm-perlapi
        state: present
        disablerepo: "*"
        enablerepo: "slurm-local"

# Create directories
- name: Create SLURM directories on all nodes
  hosts: all
  become: yes

  tasks:
    - name: Create SLURM directories
      file:
        path: "{{ item }}"
        state: directory
        owner: slurm
        group: slurm
        mode: '0755'
      loop:
        - /var/log/slurm
        - /var/spool/slurm
        - /var/spool/slurm/ctld
        - /var/spool/slurm/d
        - /etc/slurm

    - name: Create MUNGE directories
      file:
        path: "{{ item }}"
        state: directory
        owner: munge
        group: munge
        mode: '0700'
      loop:
        - /etc/munge
        - /var/log/munge
        - /var/lib/munge
        - /run/munge

# Setup MUNGE on head node
- name: Setup MUNGE on head node
  hosts: head
  become: yes

  tasks:
    - name: Check if munge key exists
      stat:
        path: /etc/munge/munge.key
      register: munge_key

    - name: Generate MUNGE key
      command: /usr/sbin/create-munge-key
      args:
        creates: /etc/munge/munge.key
      when: not munge_key.stat.exists

    - name: Set MUNGE key permissions
      file:
        path: /etc/munge/munge.key
        owner: munge
        group: munge
        mode: '0400'

    - name: Copy MUNGE key to NFS share
      copy:
        src: /etc/munge/munge.key
        dest: /nfs/shared/munge.key
        remote_src: yes
        owner: root
        group: root
        mode: '0600'

    - name: Start and enable MUNGE
      systemd:
        name: munge
        state: started
        enabled: yes

# Distribute MUNGE key to compute nodes
- name: Setup MUNGE on compute nodes
  hosts: compute
  become: yes

  tasks:
    - name: Copy MUNGE key from NFS share
      copy:
        src: /nfs/shared/munge.key
        dest: /etc/munge/munge.key
        remote_src: yes
        owner: munge
        group: munge
        mode: '0400'

    - name: Start and enable MUNGE
      systemd:
        name: munge
        state: started
        enabled: yes

# Deploy SLURM configuration
- name: Configure SLURM on all nodes
  hosts: all
  become: yes

  tasks:
    - name: Deploy slurm.conf
      template:
        src: templates/slurm.conf.j2
        dest: /etc/slurm/slurm.conf
        owner: slurm
        group: slurm
        mode: '0644'

# Start SLURM services
- name: Start SLURM controller on head node
  hosts: head
  become: yes

  tasks:
    - name: Start and enable slurmctld
      systemd:
        name: slurmctld
        state: started
        enabled: yes

- name: Start SLURM daemon on compute nodes
  hosts: compute
  become: yes

  tasks:
    - name: Start and enable slurmd
      systemd:
        name: slurmd
        state: started
        enabled: yes

# Cleanup and verification
- name: Cleanup sensitive files
  hosts: head
  become: yes

  tasks:
    - name: Remove MUNGE key from NFS share
      file:
        path: /nfs/shared/munge.key
        state: absent

- name: Verify SLURM installation
  hosts: head
  become: yes

  tasks:
    - name: Check SLURM cluster status
      command: sinfo
      register: sinfo_output
      changed_when: false

    - name: Display cluster status
      debug:
        var: sinfo_output.stdout_lines
```

### Step 8: Run the Ansible Playbook

Execute the playbook from the head node:

```bash
cd /home/ansible/slurm-ansible
ansible-playbook -i inventory.ini slurm_install_offline.yml
```

Monitor the output for any errors. The playbook will display the cluster status at the end.

### Step 9: Fix Node States if Needed

If nodes show DRAIN or INVALID state, check the reason:

```bash
scontrol show node srv-hpc-02 | grep -E "State|Reason"
```

Common issues and fixes:

#### Low RealMemory Error

If nodes are drained due to memory mismatch, update slurm.conf with correct memory values:

```bash
# Check actual memory on compute nodes
ssh srv-hpc-02 "free -m"

# Update slurm.conf with value below actual memory
sudo vim /etc/slurm/slurm.conf
```

After updating, distribute the configuration and restart services:

```bash
# Copy configuration to all nodes
ansible -i inventory.ini all -m copy \
    -a "src=/etc/slurm/slurm.conf dest=/etc/slurm/slurm.conf" --become

# Verify configurations match
ansible -i inventory.ini all -m command \
    -a "md5sum /etc/slurm/slurm.conf" --become

# Restart services
sudo systemctl restart slurmctld
ansible -i inventory.ini compute -m systemd \
    -a "name=slurmd state=restarted" --become

# Undrain nodes
sudo scontrol update nodename=srv-hpc-02 state=undrain
sudo scontrol update nodename=srv-hpc-03 state=undrain
sudo scontrol update nodename=srv-hpc-04 state=undrain
sudo scontrol update nodename=srv-hpc-05 state=undrain
```

#### Configuration Mismatch Error

If logs show "different slurm.conf" errors, ensure all nodes have identical configuration:

```bash
# Check MD5 sums
ansible -i inventory.ini all -m command \
    -a "md5sum /etc/slurm/slurm.conf" --become

# If different, copy from head node
ansible -i inventory.ini compute -m copy \
    -a "src=/etc/slurm/slurm.conf dest=/etc/slurm/slurm.conf owner=slurm group=slurm mode=0644" --become
```

### Step 10: Fix MUNGE Permissions

If job submission fails with MUNGE authentication errors:

```bash
# Fix permissions on all nodes
ansible -i inventory.ini all -m file \
    -a "path=/var/run/munge mode=0755" --become

# Restart MUNGE on all nodes
ansible -i inventory.ini all -m systemd \
    -a "name=munge state=restarted" --become

# Verify MUNGE is working
ansible -i inventory.ini all -m command \
    -a "munge -n" --become
```

### Step 11: Verify Installation

Check that all nodes are idle and ready:

```bash
sinfo
```

Expected output:

```
PARTITION AVAIL  TIMELIMIT  NODES  STATE NODELIST
compute*     up   infinite      4   idle srv-hpc-[02-05]
```

Check detailed node information:

```bash
scontrol show nodes
```

Test MUNGE authentication:

```bash
munge -n | unmunge
```

### Step 12: Install MPI Environment

On all nodes, ensure OpenMPI is available:

```bash
module load mpi/openmpi-x86_64
```

Or set environment variables directly:

```bash
export PATH=/usr/lib64/openmpi/bin:$PATH
export LD_LIBRARY_PATH=/usr/lib64/openmpi/lib:$LD_LIBRARY_PATH
```

Install mpi4py for Python MPI support:

```bash
pip install mpi4py --break-system-packages
```

## Post-Installation Tasks

### Create MPI Working Directory

```bash
mkdir -p /nfs/shared/mpi
chmod 755 /nfs/shared/mpi
```

### Create Sample Job Script

Create /nfs/shared/mpi/mpi_job.sh:

```bash
#!/bin/bash
#SBATCH --job-name=mpi_test
#SBATCH --nodes=2
#SBATCH --ntasks=4
#SBATCH --ntasks-per-node=2
#SBATCH --time=00:05:00
#SBATCH --partition=compute
#SBATCH --output=mpi_output_%j.log

export PATH=/usr/lib64/openmpi/bin:$PATH
export LD_LIBRARY_PATH=/usr/lib64/openmpi/lib:$LD_LIBRARY_PATH
export OMPI_MCA_btl_tcp_if_include=10.10.10.0/24

# Build hostfile with slots from SLURM
HOSTFILE=/tmp/hostfile_$SLURM_JOB_ID
for node in $(scontrol show hostnames $SLURM_JOB_NODELIST); do
    echo "$node slots=2"
done > $HOSTFILE

echo "=== Hostfile ==="
cat $HOSTFILE

# Run MPI
mpiexec --hostfile $HOSTFILE -n 4 python3 /nfs/shared/mpi/mpi_bcast.py

rm -f $HOSTFILE
```

### Test Job Submission

```bash
cd /nfs/shared/mpi
sbatch mpi_job.sh
squeue
```

## Installation Summary

The installation process completes the following major tasks:

1. Configured network connectivity and host resolution across all nodes
2. Established SSH key-based authentication for Ansible automation
3. Created offline package repository on NFS share
4. Deployed SLURM and MUNGE packages to all nodes via Ansible
5. Generated and distributed MUNGE authentication key
6. Configured SLURM with appropriate resource definitions
7. Started and enabled all required services
8. Verified cluster health and job submission capability

The cluster is now ready to accept and run parallel computing jobs.
