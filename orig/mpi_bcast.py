from mpi4py import MPI
import numpy as np

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# --- Step1 Broadcast a parameter to all ---
if rank == 0:
    multiplier = np.array([10.0], dtype='d')
else:
    multiplier = np.empty(1, dtype='d')

comm.Bcast(multiplier, root = 0)
print(f"Rank {rank}: received multiplier = {multiplier[0]}")

# --- Step2: Scatter work data ---
chunk_size = 2
if rank == 0:
    sendbuf = np.arange(1, size * chunk_size + 1, dtype='d') # Dynamic size
else:
    sendbuf = None
    
recvbuf = np.empty(chunk_size, dtype='d')
comm.Scatter(sendbuf, recvbuf, root=0)
print(f"Rank {rank}: received data = {recvbuf}")

# --- Step2a: Gather - collect pieces from all into root ---
sendbuf_gather = np.array([rank * 10, rank * 10 + 1], dtype = 'd')
# Only Root needs recvbuf (collects from everyone)
if rank == 0:
    recvbuf_gather = np.empty(chunk_size * size, dtype='d') # 2 elements * 4 ranks = 8
else:
    recvbuf_gather = None
    
comm.Gather(sendbuf_gather, recvbuf_gather, root=0)

if rank == 0:
    print(f"Root gathered: {recvbuf_gather}")
else:
    print(f"Rank {rank}: sent {sendbuf_gather}")

# --- Step2b Reduce: combine values (sum, max, etc.) into root ---
sendbuf_reduce= np.array([rank, rank * 10], dtype='d')

if rank == 0:
    recvbuf_reduce = np.empty(2, dtype='d')
else:
    recvbuf_reduce = None
    
comm.Reduce(sendbuf_reduce, recvbuf_reduce, op=MPI.SUM, root=0)
print(f"Rank {rank}: sent {sendbuf_reduce}")

if rank == 0:
    print(f"Root reduced (SUM): {recvbuf_reduce}")

# --- Step: 3: Allreduce: reduce + broadcast result to all ---
sendbuf_allreduce = np.array([rank, rank*10], dtype = 'd')
recvbuf_allreduce = np.empty_like(sendbuf_allreduce)

comm.Allreduce(sendbuf_allreduce, recvbuf_allreduce, op=MPI.SUM)
print(f"Rank {rank}: sent {sendbuf_allreduce}, allreduce_result = {recvbuf_allreduce}")

# --- Step4: Each Rank does local computation ---
result = recvbuf * multiplier[0]
print(f"Rank {rank}: local_result = {result}")
















