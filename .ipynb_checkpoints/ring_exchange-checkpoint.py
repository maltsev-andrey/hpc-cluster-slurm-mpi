from mpi4py import MPI
import numpy as np

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

N = 10
local_grid = np.ones(N + 2, dtype='d') * rank

# Each process has local data
local_value = np.array([rank * 10.0], dtype='d')
recv_value = np.empty(1, dtype='d')

# Ring: send to right, receive from left
left = (rank - 1) % size
right = (rank + 1) % size

# comm.Sendrecv(
#     sendbuf=local_value, 
#     dest=right, 
#     sendtag=99, 
#     recvbuf=recv_value, 
#     source=left, 
#     recvtag=99
# )
comm.Sendrecv(sendbuf=local_grid[1:2], dest=left, sendtag=0,
                            recvbuf=local_grid[0:1], source=right, recvtag=0)

comm.Sendrecv(sendbuf=local_grid[-2:-1], dest=right, sendtag=1,
                            recvbuf=local_grid[-1:], source=left, recvtag=1)

# print(f"Rank {rank}: sent {local_value[0]}, received {recv_value[0]} from rank {left}")
print(f"Rank {rank}: local_grid = {local_grid}")