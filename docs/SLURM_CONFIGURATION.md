# SLURM Configuration Guide

## Overview

SLURM (Simple Linux Utility for Resource Management) is the workload manager used to schedule and manage jobs on this HPC cluster. This document explains the configuration choices made and provides guidance for common administrative tasks.

## Configuration File Location

The primary SLURM configuration file is located at:

```
/etc/slurm/slurm.conf
```

This file must be identical on all nodes in the cluster. Any modification requires distribution to all nodes and service restart.

## Configuration Sections Explained

### Cluster Identity

```
ClusterName=hpc-cluster
SlurmctldHost=srv-hpc-01
```

| Parameter     | Value       | Description                                        |
|---------------|-------------|----------------------------------------------------|
| ClusterName   | hpc-cluster | Unique identifier for this cluster                 |
| SlurmctldHost | srv-hpc-01  | Hostname of the node running the controller daemon |

### Authentication

```
AuthType=auth/munge
CryptoType=crypto/munge
```

| Parameter  | Value        | Description                            |
|------------|--------------|----------------------------------------|
| AuthType   | auth/munge   | Use MUNGE for message authentication   |
| CryptoType | crypto/munge | Use MUNGE for cryptographic operations |

MUNGE provides secure authentication between SLURM daemons. All nodes must share the same MUNGE key and have the munge service running.

### Network Ports

```
SlurmctldPort=6817
SlurmdPort=6818
```

| Parameter     | Value | Description                              |
|---------------|-------|------------------------------------------|
| SlurmctldPort | 6817  | Port for controller daemon communication |
| SlurmdPort    | 6818  | Port for node daemon communication       |

These are the default SLURM ports. Ensure firewall rules allow traffic on these ports between all cluster nodes.

### File Paths

```
SlurmdSpoolDir=/var/spool/slurm/d
StateSaveLocation=/var/spool/slurm/ctld
SlurmctldPidFile=/run/slurmctld.pid
SlurmdPidFile=/run/slurmd.pid
```

| Parameter         | Value                 | Description                          |
|-------------------|-----------------------|--------------------------------------|
| SlurmdSpoolDir    | /var/spool/slurm/d    | Directory for slurmd temporary files |
| StateSaveLocation | /var/spool/slurm/ctld | Directory for controller state files |
| SlurmctldPidFile  | /run/slurmctld.pid    | PID file for controller daemon       |
| SlurmdPidFile     | /run/slurmd.pid       | PID file for node daemon             |

These directories must exist with proper ownership (slurm:slurm) and permissions (755).

### Logging

```
SlurmctldLogFile=/var/log/slurm/slurmctld.log
SlurmdLogFile=/var/log/slurm/slurmd.log
SlurmctldDebug=info
SlurmdDebug=info
```

| Parameter        | Value                        | Description                   |
|------------------|------------------------------|-------------------------------|
| SlurmctldLogFile | /var/log/slurm/slurmctld.log | Controller log file location  |
| SlurmdLogFile    | /var/log/slurm/slurmd.log    | Node daemon log file location |
| SlurmctldDebug   | info                         | Controller logging verbosity  |
| SlurmdDebug      | info                         | Node daemon logging verbosity |

Debug levels available: quiet, fatal, error, info, verbose, debug, debug2, debug3, debug4, debug5

### Process Tracking

```
ProctrackType=proctrack/linuxproc
ReturnToService=2
```

| Parameter       | Value               | Description                                        |
|-----------------|---------------------|----------------------------------------------------|
| ProctrackType   | proctrack/linuxproc | Use Linux /proc for process tracking               |
| ReturnToService | 2                   | Automatically return nodes to service after reboot |

ReturnToService=2 means nodes marked DOWN due to failure will automatically return to service when they come back online with valid configuration.

### Scheduling

```
SchedulerType=sched/backfill
SelectType=select/cons_tres
SelectTypeParameters=CR_Core
```

| Parameter           | Value                  | Description                             |
|---------------------|------------------------|-----------------------------------------|
| SchedulerType       | sched/backfill         | Use backfill scheduling algorithm       |
| SelectType          | select/cons_tres       | Consumable trackable resources          |
| SelectTypeParameters| CR_Core                | Track individual CPU cores as resources |

The backfill scheduler allows smaller jobs to fill gaps while larger jobs wait, improving cluster utilization.

### Timeouts

```
SlurmctldTimeout=120
SlurmdTimeout=300
InactiveLimit=0
MinJobAge=300
KillWait=30
Waittime=0
```
| Parameter        | Value | Description                                        |
|------------------|-------|----------------------------------------------------|
| SlurmctldTimeout | 120   | Seconds before backup controller takes over        |
| SlurmdTimeout    | 300   | Seconds before node marked unresponsive            |
| InactiveLimit    | 0     | Seconds before inactive job killed (0 = disabled)  |
| MinJobAge        | 300   | Minimum age before completed job purged            |
| KillWait         | 30    | Seconds between SIGTERM and SIGKILL                |
| Waittime         | 0     | Seconds between job steps                          |

### MPI Configuration

```
MpiDefault=pmix
```

| Parameter  | Value | Description                         |
|------------|-------|-------------------------------------|
| MpiDefault | pmix  | Default MPI implementation for srun |

PMIx (Process Management Interface - Exascale) provides the interface between SLURM and MPI applications.

### Node Definitions

```
NodeName=srv-hpc-02 CPUs=12 RealMemory=7600 State=UNKNOWN
NodeName=srv-hpc-03 CPUs=12 RealMemory=7600 State=UNKNOWN
NodeName=srv-hpc-04 CPUs=12 RealMemory=7600 State=UNKNOWN
NodeName=srv-hpc-05 CPUs=12 RealMemory=7600 State=UNKNOWN
```
| Parameter  | Description                               |
|----------- |-------------------------------------------|
| NodeName   | Hostname of the compute node              |
| CPUs       | Number of CPU cores available             |
| RealMemory | Available memory in megabytes             |
| State      | Initial state (UNKNOWN lets Slurm detect) |

Important: RealMemory must be less than or equal to actual available memory. Setting it higher causes nodes to be rejected with INVALID_REG status.

### Partition Definition

```
PartitionName=compute Nodes=srv-hpc-[02-05] Default=YES MaxTime=INFINITE State=UP
```
| Parameter     | Value          | Description                            |
|---------------|----------------|----------------------------------------|
| PartitionName | compute        | Name of this partition/queue           |
| Nodes         | srv-hpc-[02-05]| Nodes belonging to this partition      |
| Default       | YES            | Default partition for job submission   |
| MaxTime       | INFINITE       | Maximum job runtime allowed            |
| State         | UP             | Partition is active and accepting jobs |


## SLURM Commands Reference

### Cluster Status Commands

View partition and node status:

```bash
sinfo
```

Sample output:

```
PARTITION AVAIL  TIMELIMIT  NODES  STATE NODELIST
compute*     up   infinite      4   idle srv-hpc-[02-05]
```

View detailed node information:

```bash
scontrol show nodes
```

View specific node details:

```bash
scontrol show node srv-hpc-02
```

### Job Management Commands

Submit a batch job:

```bash
sbatch job_script.sh
```

View job queue:

```bash
squeue
```

View jobs for specific user:

```bash
squeue -u username
```

Cancel a job:

```bash
scancel job_id
```

Cancel all jobs for a user:

```bash
scancel -u username
```

View job details:

```bash
scontrol show job job_id
```

### Administrative Commands

Reconfigure SLURM (apply configuration changes):

```bash
sudo scontrol reconfigure
```

Update node state:

```bash
sudo scontrol update nodename=srv-hpc-02 state=idle
sudo scontrol update nodename=srv-hpc-02 state=drain reason="maintenance"
sudo scontrol update nodename=srv-hpc-02 state=undrain
```

View completed job history:

```bash
sacct
sacct -j job_id
sacct --starttime=2025-01-01
```

## Job Script Format

A SLURM job script consists of directives and commands:

```bash
#!/bin/bash
#SBATCH --job-name=my_job          # Job name
#SBATCH --nodes=2                   # Number of nodes
#SBATCH --ntasks=8                  # Total number of tasks
#SBATCH --ntasks-per-node=4         # Tasks per node
#SBATCH --cpus-per-task=1           # CPUs per task
#SBATCH --mem=4G                    # Memory per node
#SBATCH --time=01:00:00             # Time limit (HH:MM:SS)
#SBATCH --partition=compute         # Partition name
#SBATCH --output=output_%j.log      # Standard output file
#SBATCH --error=error_%j.log        # Standard error file

# Job commands go here
echo "Job starting on $(hostname)"
echo "Running on nodes: $SLURM_JOB_NODELIST"

# Run application
mpiexec -n $SLURM_NTASKS ./my_application
```

### Common SBATCH Directives

| Directive          | Description          | Example              |
|--------------------|----------------------|----------------------|
| --job-name         | Name for the job     | --job-name=test      |
| --nodes            | Number of nodes      | --nodes=4            |
| --ntasks           | Total tasks          | --ntasks=16          |
| --ntasks-per-node  | Tasks per node       | --ntasks-per-node=4  |
| --cpus-per-task    | CPUs per task        | --cpus-per-task=2    |
| --mem              | Memory per node      | --mem=8G             |
| --mem-per-cpu      | Memory per CPU       | --mem-per-cpu=2G     |
| --time             | Time limit           | --time=02:00:00      |
| --partition        | Partition name       | --partition=compute  |
| --output           | Output file          | --output=job_%j.out  |
| --error            | Error file           | --error=job_%j.err   |
| --exclusive        | Exclusive node access| --exclusive          |

### SLURM Environment Variables

Available within job scripts:

| Variable             | Description                 |
|----------------------|-----------------------------|
| SLURM_JOB_ID         | Unique job identifier       |
| SLURM_JOB_NAME       | Job name                    |
| SLURM_JOB_NODELIST   | List of allocated nodes     |
| SLURM_JOB_NUM_NODES  | Number of nodes             |
| SLURM_NTASKS         | Total number of tasks       |
| SLURM_TASKS_PER_NODE | Tasks per node              |
| SLURM_CPUS_PER_TASK  | CPUs per task               |
| SLURM_SUBMIT_DIR     | Directory of submission     |


## Service Management

### Starting Services

On head node:

```bash
sudo systemctl start munge
sudo systemctl start slurmctld
```

On compute nodes:

```bash
sudo systemctl start munge
sudo systemctl start slurmd
```

### Stopping Services

On head node:

```bash
sudo systemctl stop slurmctld
sudo systemctl stop munge
```

On compute nodes:

```bash
sudo systemctl stop slurmd
sudo systemctl stop munge
```

### Checking Service Status

```bash
sudo systemctl status munge
sudo systemctl status slurmctld  # head node
sudo systemctl status slurmd     # compute nodes
```

### Viewing Logs

Controller log:

```bash
sudo tail -f /var/log/slurm/slurmctld.log
```

Node daemon log:

```bash
sudo tail -f /var/log/slurm/slurmd.log
```

MUNGE log:

```bash
sudo journalctl -u munge
```

## Configuration Changes Procedure

When modifying slurm.conf:

1. Edit the configuration file on the head node:

```bash
sudo vim /etc/slurm/slurm.conf
```

2. Copy to all compute nodes:

```bash
ansible -i inventory.ini compute -m copy \
    -a "src=/etc/slurm/slurm.conf dest=/etc/slurm/slurm.conf owner=slurm group=slurm mode=0644" --become
```

3. Verify configurations match:

```bash
ansible -i inventory.ini all -m command \
    -a "md5sum /etc/slurm/slurm.conf" --become
```

4. Apply changes:

```bash
sudo scontrol reconfigure
```

For major changes, restart services:

```bash
sudo systemctl restart slurmctld
ansible -i inventory.ini compute -m systemd \
    -a "name=slurmd state=restarted" --become
```

## Troubleshooting Common Issues

### Nodes in DOWN State

Check the reason:

```bash
scontrol show node srv-hpc-02 | grep -E "State|Reason"
```

Common causes and solutions:

| Reason                 | Solution                          |
|------------------------|-----------------------------------|
| Low RealMemory         | Reduce RealMemory in slurm.conf   |
| Not responding         | Check slurmd service and network  |
| Configuration mismatch | Sync slurm.conf across nodes      |

### MUNGE Authentication Errors

Verify MUNGE is running:

```bash
systemctl status munge
```

Test MUNGE:

```bash
munge -n | unmunge
```

Check permissions:

```bash
ls -la /etc/munge/munge.key
ls -la /var/run/munge/
```

Fix permissions if needed:

```bash
sudo chmod 0400 /etc/munge/munge.key
sudo chown munge:munge /etc/munge/munge.key
sudo chmod 0755 /var/run/munge
```

### Jobs Not Starting

Check partition state:

```bash
sinfo
```

Check node availability:

```bash
scontrol show partition compute
```

Check job requirements vs available resources:

```bash
scontrol show job job_id
```

### Configuration Not Applied

Ensure all nodes have identical configuration:

```bash
ansible -i inventory.ini all -m command \
    -a "md5sum /etc/slurm/slurm.conf" --become
```

Force reconfiguration:

```bash
sudo scontrol reconfigure
```

If reconfigure fails, restart services:

```bash
sudo systemctl restart slurmctld
ansible -i inventory.ini compute -m systemd \
    -a "name=slurmd state=restarted" --become
```
