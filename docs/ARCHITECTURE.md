# SLURM Cluster Architecture Overview

## Introduction

This document describes the architectural design of the SLURM installed on HPC cluster, including network topology, storage configuration, and service distribution. The design prioritizes reliability, ease of maintenance, and suitability for parallel computing workloads.

## Physical Architecture

### Node Roles and Responsibilities

The cluster follows a traditional head node plus compute node architecture, where responsibilities are clearly separated between management and computation.

#### Head Node (srv-hpc-01)

The head node serves multiple critical functions:

1. SLURM Controller (slurmctld): Manages job scheduling, resource allocation, and cluster state
2. Login Node: Provides user access point for job submission and interactive work
3. NFS Server: Exports shared filesystem to compute nodes
4. Gateway: Provides external network access for package management and updates
5. Ansible Control Node: Executes configuration management playbooks

#### Compute Nodes (srv-hpc-02 through srv-hpc-05)

The four compute nodes are dedicated to running user workloads:

1. SLURM Daemon (slurmd): Accepts and executes jobs from the controller
2. MPI Processes: Run parallel application components
3. NFS Client: Accesses shared storage for code and data

### Hardware Specifications

Each node in the cluster shares similar hardware characteristics:

| Specification    | Value                             |
|------------------|-----------------------------------|
| CPU Cores        | 12                                |
| Memory           | 8 GB (7600 MB available to SLURM) |
| Operating System | Red Hat Enterprise Linux 9.5      |
| Kernel           | 5.14.0-503.34.1.el9_5.x86_64      |

The slight reduction in available memory (7600 MB vs 8192 MB) accounts for operating system overhead and prevents SLURM from rejecting nodes due to memory discrepancies.

## Network Architecture

### Dual Network Design

The cluster operates on two distinct networks to provide security and isolation:

#### External Network (170.168.1.0/24)

This network connects the head node to the broader infrastructure:

| Node       | IP Addres    | Purpose                            |
|------------|--------------|------------------------------------|
| srv-hpc-01 | 170.168.1.30 | External access, package downloads |

Only the head node connects to this network, providing a single point of control for external communications.

#### Internal Cluster Network (10.10.10.0/24)

This dedicated network handles all inter-node cluster traffic:

| Node       | IP Address | Purpose                      |
|------------|-------------|-----------------------------|
| srv-hpc-01 | 10.10.10.1  | Head node cluster interface |
| srv-hpc-02 | 10.10.10.11 | Compute node 1              |
| srv-hpc-03 | 10.10.10.12 | Compute node 2              |
| srv-hpc-04 | 10.10.10.13 | Compute node 3              |
| srv-hpc-05 | 10.10.10.14 | Compute node 4              |

All MPI traffic, SLURM communications, and NFS mounts operate over this internal network.

### Network Diagram

```
    +------------------+
    |  External Net    |
    |  170.168.1.0/24  |
    +--------+---------+
             |
             | 170.168.1.30
    +--------+---------+
    |   srv-hpc-01     |
    |   HEAD NODE      |
    |   Services:      |
    |   - slurmctld    |
    |   - NFS server   |
    |   - munge        |
    +--------+---------+
             | 10.10.10.1
             |
    +--------+---------+
    | Internal Cluster |
    |  10.10.10.0/24   |
    +--+-----+-----+---+
       |     |     |
       |     |     +------------------+
       |     |                        |
       |     +----------+             |
       |                |             |
+------+------+  +------+------+  +---+----------+  +-------------+
| srv-hpc-02  |  | srv-hpc-03  |  | srv-hpc-04   |  | srv-hpc-05  |
| 10.10.10.11 |  | 10.10.10.12 |  | 10.10.10.13  |  | 10.10.10.14 |
| Services:   |  | Services:   |  | Services:    |  | Services:   |
| - slurmd    |  | - slurmd    |  | - slurmd     |  | - slurmd    |
| - munge     |  | - munge     |  | - munge      |  | - munge     |
| - NFS mount |  | - NFS mount |  | - NFS mount  |  | - NFS mount |
+-------------+  +-------------+  +--------------+  +-------------+
```

### MPI Network Configuration

MPI applications require explicit network interface specification to ensure communication occurs over the internal cluster network:

```bash
export OMPI_MCA_btl_tcp_if_include=10.10.10.0/24
```

Without this setting, OpenMPI may attempt to use the external network interface, causing communication failures or warnings.

## Storage Architecture

### NFS Shared Storage

The cluster uses NFS to provide a shared filesystem accessible from all nodes:

| Parameter   | Value                           |
|-------------|---------------------------------|
| Export Path | /nfs/shared                     |
| Mount Point | /nfs/shared (same on all nodes) |
| Server      | srv-hpc-01                      |

### Storage Usage

The shared storage serves several purposes:

#### Application Code Directory (/nfs/shared/mpi)

Contains MPI programs and job scripts that need to be accessible from any compute node where a job might run.

#### Package Repository (/nfs/shared/slurm-repo)

Stores RPM packages for offline installation on compute nodes that lack internet access. This local repository contains:

1. SLURM packages (slurm, slurm-libs, slurm-slurmd, slurm-slurmctld)
2. MUNGE packages (munge, munge-libs)
3. All required dependencies

#### Repository Structure

```
/nfs/shared/
    slurm-repo/
        repodata/
        slurm-22.05.9-1.el9.x86_64.rpm
        slurm-libs-22.05.9-1.el9.x86_64.rpm
        slurm-slurmd-22.05.9-1.el9.x86_64.rpm
        slurm-slurmctld-22.05.9-1.el9.x86_64.rpm
        munge-0.5.13-13.el9.x86_64.rpm
        munge-libs-0.5.13-13.el9.x86_64.rpm
        ... (additional dependencies)
    mpi/
        mpi_bcast.py
        ring_exchange.py
        mpi_job.sh
```

## Service Architecture

### SLURM Components

The SLURM workload manager consists of several daemons distributed across the cluster:

#### slurmctld (Controller Daemon)

Runs on the head node and manages:

1. Job queue and scheduling decisions
2. Resource allocation across compute nodes
3. Cluster state and node health monitoring
4. User authentication and authorization

#### slurmd (Node Daemon)

Runs on each compute node and handles:

1. Job execution and process management
2. Resource reporting to the controller
3. Job step launching and monitoring

### MUNGE Authentication

MUNGE provides authentication services for SLURM communications:

1. All nodes share the same cryptographic key (/etc/munge/munge.key)
2. The munge daemon runs on every node
3. SLURM uses MUNGE to verify message authenticity between daemons

### Service Dependencies

The following diagram shows service startup dependencies:

```
    +-------------+
    |   munge     |
    +------+------+
           |
           | (authentication required)
           |
    +------+------+
    |   SLURM     |
    | slurmctld   |  (head node)
    | slurmd      |  (compute nodes)
    +-------------+
```

MUNGE must be running and healthy before SLURM services can start successfully.

## Partition Configuration

The cluster defines a single partition named "compute" that includes all four compute nodes:

| Parameter      | Value           |
|----------------|-----------------|
| Partition Name | compute         |
| Nodes          | srv-hpc-[02-05] |
| Default        | Yes             |
| Max Time       | Infinite        |
| State          | UP              |

This configuration allows jobs to use any combination of the four compute nodes up to the full cluster capacity of 48 CPU cores.

## Resource Allocation

### Per-Node Resources

Each compute node offers the following resources to SLURM:

| Resource         | Value   |
|------------------|---------|
| CPUs             | 12      |
| Real Memory      | 7600 MB |
| Sockets          | 12      |
| Cores per Socket | 1       |
| Threads per Core | 1       |

### Total Cluster Resources

| Resource     | Value     |
|--------------|-----------|
| Total Nodes  | 4         |
| Total CPUs   | 48        |
| Total Memory | 30,400 MB |

## Security Considerations

### Network Isolation

The internal cluster network provides isolation from external threats:

1. Compute nodes have no direct internet access
2. All external communication routes through the head node
3. Firewall rules can be applied at the head node

### Authentication

MUNGE provides cryptographic authentication:

1. Shared secret key generated on head node
2. Key distributed securely to compute nodes
3. All SLURM messages authenticated before processing

### File Permissions

Critical files maintain strict permissions:

| File                  | Permissions | Owner       |
|-----------------------|-------------|-------------|
| /etc/munge/munge.key  | 0400        | munge:munge |
| /var/run/munge        | 0755        | munge:munge |
| /etc/slurm/slurm.conf | 0644        | slurm:slurm |
| /var/log/slurm        | 0755        | slurm:slurm |

## Design Decisions and Rationale

### Why Separate Networks

The dual network design provides several benefits:

1. Security isolation between cluster traffic and external access
2. Predictable MPI communication paths
3. Simplified firewall rules and access control
4. Bandwidth isolation for high-performance computing traffic

### Why NFS for Shared Storage

NFS was chosen for its simplicity and compatibility:

1. Native Linux support without additional software
2. Familiar administrative tools and procedures
3. Sufficient performance for job scripts and small data files
4. Easy setup and maintenance

### Why Offline Package Repository

The offline repository approach addresses air-gapped compute nodes:

1. Compute nodes lack internet access by design
2. Packages downloaded once on head node
3. Local repository created on NFS share
4. Consistent package versions across all nodes

### Why SLURM

SLURM was selected as the workload manager for several reasons:

1. Industry standard for HPC clusters
2. Active development and community support
3. Flexible resource management
4. Good documentation and learning resources
5. Compatible with MPI implementations

## Scalability Considerations

The current architecture supports future expansion:

1. Additional compute nodes can be added to the internal network
2. The partition configuration easily extends to new nodes
3. NFS shared storage scales with storage capacity
4. SLURM controller can manage hundreds of nodes

To add a new compute node, the following steps would be required:

1. Install operating system and configure networking
2. Add node entry to /etc/hosts on all nodes
3. Install SLURM and MUNGE from local repository
4. Copy MUNGE key and SLURM configuration
5. Start services and update partition definition
