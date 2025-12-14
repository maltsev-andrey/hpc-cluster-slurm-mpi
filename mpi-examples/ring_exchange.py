"""
MPI Ring Exchange and Ghost Cell Communication Example

This program demonstrates:
- Ring topology communication using Sendrecv
- Ghost cell/halo exchange pattern for boundary data

Run with: mpiexec -n 4 python3 ring_exchange.py
"""

from mpi4py import MPI
import numpy as np

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# Grid size (interior cells)
N = 10

# Create local grid with ghost cells at boundaries
# Layout: [ghost_left, interior_cells..., ghost_right]
local_grid = np.ones(N + 2, dtype='d') * rank

# Calculate neighbors in ring topology
left = (rank - 1) % size
right = (rank + 1) % size

print(f"Rank {rank}: left neighbor = {left}, right neighbor = {right}")

# Ghost cell exchange
# Each process sends its boundary values to neighbors
# and receives neighbor boundary values into ghost cells

# Exchange with left neighbor:
# Send my leftmost interior cell to left, receive from right into right ghost
comm.Sendrecv(sendbuf=local_grid[1:2], dest=left, sendtag=0,
              recvbuf=local_grid[-1:], source=right, recvtag=0)

# Exchange with right neighbor:
# Send my rightmost interior cell to right, receive from left into left ghost
comm.Sendrecv(sendbuf=local_grid[-2:-1], dest=right, sendtag=1,
              recvbuf=local_grid[0:1], source=left, recvtag=1)

print(f"Rank {rank}: local_grid = {local_grid}")

# Explanation of results:
# For rank 0 with 4 processes:
#   left ghost (index 0) = value from rank 3 (its rightmost interior)
#   interior (indices 1-10) = all 0s (original values)
#   right ghost (index 11) = value from rank 1 (its leftmost interior)

# This pattern is essential for:
# - Finite difference methods
# - Stencil computations
# - Image processing with boundary conditions
# - Any algorithm requiring neighbor data
