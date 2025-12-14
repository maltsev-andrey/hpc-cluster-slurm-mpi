# Troubleshooting Guide

## Overview

This document provides solutions to common issues encountered during HPC cluster operation. Each section describes the problem, diagnostic steps, and resolution procedures.

## SLURM Issues

### Nodes in DRAIN State

Symptoms:
- sinfo shows nodes with state "drain"
- Jobs remain pending with reason "Resources"

Diagnosis:

```bash
scontrol show node srv-hpc-02 | grep -E "State|Reason"
```

Common causes and solutions:

#### Low RealMemory

Error message: "Low RealMemory (reported:7681 < 100.00% of configured:8000)"

The configured memory in slurm.conf exceeds actual available memory.

Solution:

1. Check actual memory on the node:

```bash
ssh srv-hpc-02 "free -m"
```

2. Update slurm.conf with a value below actual memory:

```bash
sudo vim /etc/slurm/slurm.conf
# Change: NodeName=srv-hpc-02 CPUs=12 RealMemory=7600 State=UNKNOWN
```

3. Distribute configuration and restart services:

```bash
ansible -i inventory.ini all -m copy \
    -a "src=/etc/slurm/slurm.conf dest=/etc/slurm/slurm.conf" --become
sudo systemctl restart slurmctld
ansible -i inventory.ini compute -m systemd \
    -a "name=slurmd state=restarted" --become
```

4. Undrain the nodes:

```bash
sudo scontrol update nodename=srv-hpc-02 state=undrain
sudo scontrol update nodename=srv-hpc-03 state=undrain
sudo scontrol update nodename=srv-hpc-04 state=undrain
sudo scontrol update nodename=srv-hpc-05 state=undrain
```

### Nodes in INVALID State

Symptoms:
- sinfo shows nodes with state "inval"
- Log shows "different slurm.conf" errors

Diagnosis:

```bash
sudo tail -50 /var/log/slurm/slurmctld.log | grep -i error
```

Cause: Configuration mismatch between head node and compute nodes.

Solution:

1. Verify configuration checksums:

```bash
ansible -i inventory.ini all -m command \
    -a "md5sum /etc/slurm/slurm.conf" --become
```

2. If checksums differ, copy from head node:

```bash
ansible -i inventory.ini compute -m copy \
    -a "src=/etc/slurm/slurm.conf dest=/etc/slurm/slurm.conf owner=slurm group=slurm mode=0644" --become
```

3. Restart all services:

```bash
sudo systemctl restart slurmctld
ansible -i inventory.ini compute -m systemd \
    -a "name=slurmd state=restarted" --become
```

### Jobs Stuck in Pending State

Symptoms:
- Jobs remain in PD (pending) state
- squeue shows reason codes

Diagnosis:

```bash
squeue -l
scontrol show job <job_id>
```

Common reasons and solutions:
| Reason         | Cause                            | Solution                               |
|----------------|----------------------------------|----------------------------------------|
| Resources      | Not enough available resources   | Wait or request fewer resources        |
| Priority       | Other jobs have higher priority  | Wait or adjust priority                |
| PartitionDown  | Partition is disabled            | Enable partition with `scontrol`       |
| NodeDown       | Required nodes are down          | Fix node issues                        |
| InvalidAccount | Account does not exist           | Check account configuration            |


### Controller Not Starting

Symptoms:
- slurmctld service fails to start
- Jobs cannot be submitted

Diagnosis:

```bash
sudo systemctl status slurmctld
sudo journalctl -u slurmctld -n 50
sudo tail -50 /var/log/slurm/slurmctld.log
```

Common causes:

1. MUNGE not running:

```bash
sudo systemctl status munge
sudo systemctl start munge
sudo systemctl start slurmctld
```

2. Incorrect file permissions:

```bash
sudo chown -R slurm:slurm /var/log/slurm
sudo chown -R slurm:slurm /var/spool/slurm
sudo chmod 755 /var/log/slurm
sudo chmod 755 /var/spool/slurm
```

3. Configuration syntax error:

```bash
slurmd -C  # Check configuration
```

## MUNGE Issues

### Authentication Failures

Symptoms:
- "Munge encode failed" errors
- "Protocol authentication error" when submitting jobs

Diagnosis:

```bash
munge -n | unmunge
sudo systemctl status munge
ls -la /etc/munge/munge.key
ls -la /var/run/munge/
```

#### Permission Denied on Socket

Error: "Failed to access /var/run/munge/munge.socket.2: Permission denied"

Solution:

```bash
sudo chmod 755 /var/run/munge
sudo systemctl restart munge
```

Apply to all nodes if needed:

```bash
ansible -i inventory.ini all -m file \
    -a "path=/var/run/munge mode=0755" --become
ansible -i inventory.ini all -m systemd \
    -a "name=munge state=restarted" --become
```

#### Key Mismatch

Symptoms: MUNGE works on some nodes but not others

Cause: Nodes have different MUNGE keys

Solution:

1. Generate new key on head node:

```bash
sudo /usr/sbin/create-munge-key --force
sudo chown munge:munge /etc/munge/munge.key
sudo chmod 400 /etc/munge/munge.key
```

2. Distribute to all compute nodes:

```bash
for node in srv-hpc-02 srv-hpc-03 srv-hpc-04 srv-hpc-05; do
    sudo scp /etc/munge/munge.key $node:/etc/munge/
    ssh $node "sudo chown munge:munge /etc/munge/munge.key && sudo chmod 400 /etc/munge/munge.key"
done
```

3. Restart MUNGE on all nodes:

```bash
ansible -i inventory.ini all -m systemd \
    -a "name=munge state=restarted" --become
```

4. Verify:

```bash
ansible -i inventory.ini all -m command -a "munge -n" --become
```

## MPI Issues

### Wrong Network Interface

Symptoms:
- Warning about invalid btl_tcp_if_include value
- MPI communication failures between nodes

Error message: "WARNING: An invalid value was given for btl_tcp_if_include"

Cause: MPI is trying to use wrong network interface

Solution:

Set the correct network before running MPI:

```bash
export OMPI_MCA_btl_tcp_if_include=10.10.10.0/24
```

In job scripts:

```bash
#!/bin/bash
#SBATCH ...
export OMPI_MCA_btl_tcp_if_include=10.10.10.0/24
mpiexec ...
```

### Not Enough Slots

Symptoms:
- Error "There are not enough slots available"

Cause: MPI does not know how many processes each host can run

Solution:

Specify slots in the hostfile or command:

```bash
# Command line
mpiexec --host srv-hpc-02:2,srv-hpc-03:2 -n 4 python3 program.py

# Hostfile
echo "srv-hpc-02 slots=2" > hostfile
echo "srv-hpc-03 slots=2" >> hostfile
mpiexec --hostfile hostfile -n 4 python3 program.py
```

### Buffer Truncation Error

Symptoms:
- MPI_ERR_TRUNCATE error
- Program crashes during collective operations

Cause: Receive buffer is smaller than sent data

Example error scenario:

```python
# 8 processes but buffer sized for 4
sendbuf = np.array([1,2,3,4,5,6,7,8], dtype='d')  # 8 elements
recvbuf = np.empty(2, dtype='d')  # Only 2 elements per process
# With 8 processes: 8/8 = 1 element each, but buffer expects 2
```

Solution:

Calculate buffer sizes based on number of processes:

```python
size = comm.Get_size()
chunk_size = 2
if rank == 0:
    sendbuf = np.arange(1, size * chunk_size + 1, dtype='d')
else:
    sendbuf = None
recvbuf = np.empty(chunk_size, dtype='d')
comm.Scatter(sendbuf, recvbuf, root=0)
```

### ORTE Daemon Failure

Symptoms:
- "ORTE daemon has unexpectedly failed" error
- MPI processes fail to start on remote nodes

Cause: Network connectivity or SSH issues between nodes

Diagnosis:

1. Test SSH connectivity:

```bash
ssh srv-hpc-02 hostname
ssh srv-hpc-03 hostname
```

2. Test network connectivity:

```bash
ping -c 3 10.10.10.11
ping -c 3 10.10.10.12
```

3. Check firewall:

```bash
ansible -i inventory.ini compute -m command \
    -a "firewall-cmd --state" --become
```

Solution:

If firewall is blocking, open required ports:

```bash
ansible -i inventory.ini compute -m command \
    -a "firewall-cmd --add-port=1024-65535/tcp --permanent" --become
ansible -i inventory.ini compute -m command \
    -a "firewall-cmd --reload" --become
```

## Package Installation Issues

### Dependency Resolution Failures

Symptoms:
- DNF reports missing dependencies
- Package installation fails on compute nodes

Cause: Local repository missing required packages

Solution:

1. On head node, download missing packages:

```bash
dnf download --resolve --destdir=/nfs/shared/slurm-repo <package_name>
```

2. Rebuild repository metadata:

```bash
createrepo --update /nfs/shared/slurm-repo
```

3. Clean cache on compute nodes:

```bash
ansible -i inventory.ini compute -m command \
    -a "dnf clean all" --become
```

### Repository Not Found

Symptoms:
- "Cannot download repomd.xml" error
- Repository metadata errors

Cause: Local repository not configured or NFS not mounted

Solution:

1. Verify NFS mount:

```bash
ansible -i inventory.ini compute -m command \
    -a "ls /nfs/shared/slurm-repo" --become
```

2. Recreate repository configuration:

```bash
ansible -i inventory.ini compute -m copy \
    -a "dest=/etc/yum.repos.d/slurm-local.repo content='[slurm-local]
name=SLURM Local Repository
baseurl=file:///nfs/shared/slurm-repo
enabled=1
gpgcheck=0
priority=1'" --become
```

## Network Issues

### Nodes Cannot Communicate

Symptoms:
- SSH between nodes fails
- MPI cannot connect to remote nodes

Diagnosis:

```bash
# From head node
ping 10.10.10.11
ssh srv-hpc-02 hostname

# Check routing
ip route
```

Common causes:

1. Incorrect /etc/hosts entries
2. Firewall blocking traffic
3. Network interface not configured

Solution:

Verify /etc/hosts on all nodes:

```bash
ansible -i inventory.ini all -m command \
    -a "cat /etc/hosts" --become
```

Ensure entries match:

```
10.10.10.1      srv-hpc-01 hpc-head
10.10.10.11     srv-hpc-02
10.10.10.12     srv-hpc-03
10.10.10.13     srv-hpc-04
10.10.10.14     srv-hpc-05
```

### NFS Mount Failures

Symptoms:
- /nfs/shared is empty or not accessible
- "Stale file handle" errors

Diagnosis:

```bash
mount | grep nfs
ls /nfs/shared
```

Solution:

1. Remount NFS:

```bash
sudo umount /nfs/shared
sudo mount -a
```

2. Check NFS server status on head node:

```bash
sudo systemctl status nfs-server
sudo exportfs -v
```

## Service Recovery Procedures

### Complete SLURM Restart

When SLURM is in an inconsistent state:

```bash
# Stop all services
ansible -i inventory.ini compute -m systemd \
    -a "name=slurmd state=stopped" --become
sudo systemctl stop slurmctld

# Clear state (optional, use with caution)
sudo rm -rf /var/spool/slurm/ctld/*
ansible -i inventory.ini compute -m command \
    -a "rm -rf /var/spool/slurm/d/*" --become

# Restart services
sudo systemctl start slurmctld
ansible -i inventory.ini compute -m systemd \
    -a "name=slurmd state=started" --become

# Verify
sinfo
```

### Complete MUNGE Restart

When authentication is failing cluster-wide:

```bash
# Stop all SLURM services first
ansible -i inventory.ini compute -m systemd \
    -a "name=slurmd state=stopped" --become
sudo systemctl stop slurmctld

# Restart MUNGE on all nodes
ansible -i inventory.ini all -m systemd \
    -a "name=munge state=restarted" --become

# Verify MUNGE
ansible -i inventory.ini all -m command \
    -a "munge -n" --become

# Restart SLURM services
sudo systemctl start slurmctld
ansible -i inventory.ini compute -m systemd \
    -a "name=slurmd state=started" --become
```

## Log File Locations
| Service   | Location                      | Node    |
|-----------|-------------------------------|---------|
| slurmctld | /var/log/slurm/slurmctld.log  | Head    |
| slurmd    | /var/log/slurm/slurmd.log     | Compute |
| munge     | journalctl -u munge           | All     |

## Diagnostic Commands Quick Reference

```bash
# Cluster status
sinfo
squeue
scontrol show nodes
scontrol show partitions

# Service status
systemctl status slurmctld
systemctl status slurmd
systemctl status munge

# Configuration verification
slurmd -C                             # Show detected configuration
scontrol show config                  # Show running configuration
md5sum /etc/slurm/slurm.conf          # Verify configuration sync

# MUNGE testing
munge -n | unmunge                    # Test local MUNGE
munge -n | ssh srv-hpc-02 unmunge     # Test cross-node MUNGE

# Network testing
ping 10.10.10.11                      # Test connectivity
ssh srv-hpc-02 hostname               # Test SSH

# Log viewing
tail -f /var/log/slurm/slurmctld.log  # Follow controller log
tail -f /var/log/slurm/slurmd.log     # Follow node log
journalctl -u munge -f                # Follow MUNGE log
```
