"""
MPI Collective Operations Example

This program demonstrates the fundamental MPI collective operations:
- Broadcast (Bcast)
- Scatter
- Gather
- Reduce
- Allreduce

Run with: mpiexec -n 4 python3 mpi_bcast.py
"""

from mpi4py import MPI
import numpy as np

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# Step 1: Broadcast a parameter to all processes
# Root process has the data, all others receive it
if rank == 0:
    multiplier = np.array([10.0], dtype='d')
else:
    multiplier = np.empty(1, dtype='d')

comm.Bcast(multiplier, root=0)
print(f"Rank {rank}: received multiplier = {multiplier[0]}")

# Step 2: Scatter work data
# Root divides data and sends pieces to all processes
chunk_size = 2
if rank == 0:
    sendbuf = np.arange(1, size * chunk_size + 1, dtype='d')
else:
    sendbuf = None

recvbuf = np.empty(chunk_size, dtype='d')
comm.Scatter(sendbuf, recvbuf, root=0)
print(f"Rank {rank}: received data = {recvbuf}")

# Step 3: Gather results back to root
# All processes send data, root collects it
sendbuf_gather = np.array([rank * 10, rank * 10 + 1], dtype='d')

if rank == 0:
    recvbuf_gather = np.empty(chunk_size * size, dtype='d')
else:
    recvbuf_gather = None

comm.Gather(sendbuf_gather, recvbuf_gather, root=0)

if rank == 0:
    print(f"Root gathered: {recvbuf_gather}")
else:
    print(f"Rank {rank}: sent {sendbuf_gather}")

# Step 4: Reduce - combine values using an operation
# All processes contribute, root gets combined result
sendbuf_reduce = np.array([rank, rank * 10], dtype='d')

if rank == 0:
    recvbuf_reduce = np.empty(2, dtype='d')
else:
    recvbuf_reduce = None

comm.Reduce(sendbuf_reduce, recvbuf_reduce, op=MPI.SUM, root=0)
print(f"Rank {rank}: sent {sendbuf_reduce}")

if rank == 0:
    print(f"Root reduced (SUM): {recvbuf_reduce}")

# Step 5: Allreduce - reduce and broadcast result to all
# All processes get the combined result
sendbuf_allreduce = np.array([rank, rank * 10], dtype='d')
recvbuf_allreduce = np.empty_like(sendbuf_allreduce)

comm.Allreduce(sendbuf_allreduce, recvbuf_allreduce, op=MPI.SUM)
print(f"Rank {rank}: sent {sendbuf_allreduce}, allreduce_result = {recvbuf_allreduce}")

# Step 6: Local computation using scattered data
result = recvbuf * multiplier[0]
print(f"Rank {rank}: local_result = {result}")
