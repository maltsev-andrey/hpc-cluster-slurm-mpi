# HPC Cluster. SLURM Installation and Configuration Guide
![RHEL](https://img.shields.io/badge/RHEL-9.5-EE0000?logo=redhat&logoColor=white)
![SLURM](https://img.shields.io/badge/SLURM-22.05.9-0078D4)
![OpenMPI](https://img.shields.io/badge/OpenMPI-Enabled-orange)
![Nodes](https://img.shields.io/badge/Nodes-5-brightgreen)
![CPUs](https://img.shields.io/badge/CPUs-48_Cores-blue)
![GPU](https://img.shields.io/badge/GPU-Tesla_P100-76B900?logo=nvidia&logoColor=white)
![Status](https://img.shields.io/badge/Status-Production-success)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Project Overview

This repository documents the complete installation, configuration, and operation of a High-Performance Computing (HPC) cluster built from scratch. The project demonstrates practical experience with parallel computing infrastructure, job scheduling systems, and distributed computing technologies.

The cluster consists of five physical servers running Red Hat Enterprise Linux 9.5, configured with SLURM workload manager for job scheduling and OpenMPI for parallel computing applications. This documentation serves as both a reference guide and a portfolio piece showcasing hands-on HPC administration skills.

## Cluster Specifications

### Hardware Configuration

| Node           | Hostname   | Role              | IP Address (Cluster)| CPUs | Memory |
|----------------|------------|-------------------|---------------------|------|--------|
| Head Node      | srv-hpc-01 | Controller, Login | 10.10.10.1          | 12   | 8 GB   |
| Compute Node 1 | srv-hpc-02 | Worker            | 10.10.10.11         | 12   | 8 GB   |
| Compute Node 2 | srv-hpc-03 | Worker            | 10.10.10.12         | 12   | 8 GB   |
| Compute Node 3 | srv-hpc-04 | Worker            | 10.10.10.13         | 12   | 8 GB   |
| Compute Node 4 | srv-hpc-05 | Worker            | 10.10.10.14         | 12   | 8 GB   |

### Software Stack

| Component        | Version  | Purpose                            |
|------------------|----------|------------------------------------|
| Operating System | RHEL 9.5 | Base system                        |
| SLURM            | 22.05.9  | Workload manager and job scheduler |
| OpenMPI          | Sys.def. | Message Passing Interface          |
| MUNGE            | 0.5.13   | Authentication service             |
| Python           | 3.x      | Scripting and MPI applications     |
| mpi4py           | Latest   | Python MPI bindings                |
| Ansible          | Latest   | Configuration management           |

### Network Architecture

The cluster operates on a dedicated internal network (10.10.10.0/24) isolated from the external network. Only the head node (srv-hpc-01) has connectivity to both networks, enabling it to serve as a gateway for package downloads and external communications.
```graph TB
    %% Top-level layout
    %% External -> Head -> Internal

    %% External network
    subgraph EXT["External Network (170.168.1.0/24)"]
        direction TB
        User[User]
        Internet[Internet]
    end

    %% Head node
    subgraph HEAD["Head Node (srv-hpc-01)"]
        direction TB
        SSH[SSH Gateway]
        Scheduler[Job Scheduler]
        NFS[NFS Server]
    end

    %% Internal cluster network
    subgraph INT["Internal Cluster Network (10.10.10.0/24)"]
        direction LR
        CN1[srv-hpc-02<br/>6 cores]
        CN2[srv-hpc-03<br/>6 cores]
        CN3[srv-hpc-04<br/>6 cores]
        CN4[srv-hpc-05<br/>6 cores]
    end

    %% Connections
    User -->|SSH| SSH
    Internet -->|Updates / Packages| HEAD
    SSH -->|Jump host SSH| HEAD
    NFS -->|Shared storage (NFS)| CN1
    NFS --> CN2
    NFS --> CN3
    NFS --> CN4
    Scheduler -->|MPI job launch| CN1
    Scheduler --> CN2
    Scheduler --> CN3
    Scheduler --> CN4

    %% Grouping edges from head to internal (optional visual helper)
    HEAD --- INT

    %% Styles
    style EXT  fill:#f0f0f0,stroke:#999,stroke-width:1px
    style HEAD fill:#e1f5ff,stroke:#339,stroke-width:1px
    style INT  fill:#fff4e1,stroke:#c90,stroke-width:1px

```


```
                          External Network (170.168.1.0/24)
                                      |
                                      |
                              +---------------+
                              |  srv-hpc-01   |
                              |  (Head Node)  |
                              | 170.168.1.30  |
                              |  10.10.10.1   |
                              +---------------+
                                      |
            Internal Cluster Network (10.10.10.0/24)
                                      |
          +-------------+-------------+-------------+
          |             |             |             |
   +------------+ +------------+ +------------+ +------------+
   | srv-hpc-02 | | srv-hpc-03 | | srv-hpc-04 | | srv-hpc-05 |
   | 10.10.10.11| | 10.10.10.12| | 10.10.10.13| | 10.10.10.14|
   +------------+ +------------+ +------------+ +------------+
        Compute       Compute       Compute       Compute
        Node 1        Node 2        Node 3        Node 4
```

### Shared Storage

The cluster utilizes NFS (Network File System) for shared storage, mounted at `/nfs/shared` across all nodes. This shared filesystem is used for:

- MPI application code and scripts
- Job submission scripts
- Shared libraries and dependencies
- Offline package repository for air-gapped installation

## Documentation Structure

This repository contains the following documentation:

| Document                                           | Description                                 |
|----------------------------------------------------|---------------------------------------------|
| [Architecture Overview](docs/ARCHITECTURE.md)      | Detailed cluster arch. and design decisions |
| [Installation Guide](docs/INSTALLATION.md)         | Step-by-step installation procedures        |
| [SLURM Configuration](docs/SLURM_CONFIGURATION.md) | Workload manager setup and configuration    |
| [MPI Programming Guide](docs/MPI_GUIDE.md)         | MPI concepts and job submission             |
| [Troubleshooting](docs/TROUBLESHOOTING.md)         | Common issues and solutions                 |

## Key Achievements

### Infrastructure Accomplishments

1. Designed and implemented a five-node HPC cluster architecture with proper network segmentation
2. Configured offline package installation for air-gapped compute nodes using NFS-based local repository
3. Automated cluster deployment using Ansible playbooks for reproducible infrastructure
4. Established MUNGE authentication for secure inter-node communication
5. Configured SLURM workload manager with proper resource allocation and job scheduling

### Technical Skills ------

1. Linux system administration on Red Hat Enterprise Linux
2. Network configuration and troubleshooting in isolated environments
3. Ansible automation for multi-node deployments
4. SLURM workload manager installation and configuration
5. MPI programming concepts including collective operations
6. Debugging parallel applications across distributed systems

## Quick Start Guide

### Checking Cluster Status

```bash
# View all nodes and their states
sinfo

# Expected output for healthy cluster
PARTITION AVAIL  TIMELIMIT  NODES  STATE NODELIST
compute*     up   infinite      4   idle srv-hpc-[02-05]
```

### Submitting a Job

```bash
# Navigate to shared MPI directory
cd /nfs/shared/mpi

# Submit a job
sbatch mpi_job.sh

# Monitor job queue
squeue

# View job output
cat mpi_output_<jobid>.log
```

### Running Interactive MPI Commands

```bash
# Load MPI environment
export PATH=/usr/lib64/openmpi/bin:$PATH
export LD_LIBRARY_PATH=/usr/lib64/openmpi/lib:$LD_LIBRARY_PATH
export OMPI_MCA_btl_tcp_if_include=10.10.10.0/24

# Run MPI application across nodes
mpiexec --host srv-hpc-02:2,srv-hpc-03:2 -n 4 python3 /nfs/shared/mpi/mpi_bcast.py
```

## Project Files

### Ansible Playbooks

The `ansible/` directory contains automation scripts for cluster deployment:

| File                      | Purpose                                    |
|---------------------------|--------------------------------------------|
| inventory.ini             | Node definitions and connection parameters |
| slurm_install_offline.yml | Main playbook for SLURM installation       |
| download_packages.sh      | Script to download packages to NFS share   |
| templates/slurm.conf.j2   | SLURM configuration template               |

### MPI Examples

The `mpi-examples/` directory contains sample MPI programs demonstrating various collective operations:

| File             | Concepts Demonstrated                         |
|------------------|-----------------------------------------------|
| mpi_bcast.py     | Broadcast, Scatter, Gather, Reduce, Allreduce |
| ring_exchange.py | Point-to-point communication, Sendrecv        |
| mpi_job.sh       | SLURM job submission script                   |

## Lessons Learned

Throughout this project, several important lessons emerged:

1. Configuration consistency is critical in distributed systems. The SLURM configuration file must be identical across all nodes, and even minor differences cause registration failures.

2. Air-gapped installations require careful dependency management. The offline package repository approach using NFS proved effective for compute nodes without internet access.

3. Network interface specification is essential for MPI. In multi-homed environments, explicitly setting the network interface prevents communication failures.

4. Memory and CPU specifications in SLURM must match actual hardware. Overestimating resources causes nodes to enter DRAIN state with INVALID_REG errors.

5. MUNGE authentication permissions require careful attention. The munge.key file permissions and socket directory access must be correctly configured on all nodes.

## Future Enhancements

Planned improvements for this cluster include:

1. GPU integration using the Tesla P100 card for CUDA-enabled workloads
2. Implementation of SLURM accounting for usage tracking
3. Configuration of job arrays for parameter sweep studies
4. Integration with environment modules for software version management
5. Implementation of backup and disaster recovery procedures

## Author
This HPC cluster was designed, built, and documented as a learning project to develop practical skills in high-performance computing infrastructure and parallel programming.

## License

This documentation is provided for educational purposes. Feel free to use it as a reference for your own HPC projects.
