#!/bin/bash
#
# SLURM Job Script for MPI Applications
#
# This script demonstrates how to submit MPI jobs to the cluster
# using SLURM workload manager.
#

#SBATCH --job-name=mpi_test           # Job name displayed in queue
#SBATCH --nodes=4                      # Number of nodes requested
#SBATCH --ntasks=8                     # Total number of MPI tasks
#SBATCH --ntasks-per-node=2            # MPI tasks per node
#SBATCH --time=00:05:00                # Maximum runtime (HH:MM:SS)
#SBATCH --partition=compute            # Partition/queue name
#SBATCH --output=mpi_output_%j.log     # Standard output file (%j = job ID)

# Set up MPI environment
export PATH=/usr/lib64/openmpi/bin:$PATH
export LD_LIBRARY_PATH=/usr/lib64/openmpi/lib:$LD_LIBRARY_PATH

# Configure MPI to use correct network interface
# This is critical for clusters with multiple networks
export OMPI_MCA_btl_tcp_if_include=10.10.10.0/24

# Build hostfile from SLURM allocation
# This ensures MPI knows which nodes and how many slots are available
HOSTFILE=/tmp/hostfile_$SLURM_JOB_ID

for node in $(scontrol show hostnames $SLURM_JOB_NODELIST); do
    echo "$node slots=$SLURM_NTASKS_PER_NODE"
done > $HOSTFILE

# Display job information
echo "============================================"
echo "Job ID: $SLURM_JOB_ID"
echo "Job Name: $SLURM_JOB_NAME"
echo "Nodes: $SLURM_JOB_NODELIST"
echo "Tasks: $SLURM_NTASKS"
echo "Tasks per node: $SLURM_NTASKS_PER_NODE"
echo "============================================"
echo ""
echo "=== Hostfile ==="
cat $HOSTFILE
echo ""
echo "=== Starting MPI Application ==="
echo ""

# Run MPI application
mpiexec --hostfile $HOSTFILE -n $SLURM_NTASKS python3 /nfs/shared/mpi/mpi_bcast.py

# Clean up temporary hostfile
rm -f $HOSTFILE

echo ""
echo "=== Job Complete ==="
