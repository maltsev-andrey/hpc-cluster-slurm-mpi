#!/bin/bash

#SBATCH --job-name=mpi_test
#SBATCH --nodes=4
#SBATCH --ntasks=8
#SBATCH --ntasks-per-node=2
#SBATCH --time=00:05:00
#SBATCH --partition=compute
#SBATCH --output=mpi_output_%j.log

export PATH=/usr/lib64/openmpi/bin:$PATH
export LD_LIBRARY_PATH=/usr/lib64/openmpi/lib:$LD_LIBRARY_PATH
export OMPI_MCA_btl_tcp_if_include=10.10.10.0/24

# Build hostfile from SLURM
HOSTFILE=/tmp/hostfile_$SLURM_JOB_ID
for node in $(scontrol show hostnames $SLURM_JOB_NODELIST); do
    echo "$node slots=2"
done > $HOSTFILE

echo "=== Hostfile ==="
cat $HOSTFILE

# Run MPI
mpiexec --hostfile $HOSTFILE -n 8 python3 /nfs/shared/mpi/mpi_bcast.py

rm -f $HOSTFILE

