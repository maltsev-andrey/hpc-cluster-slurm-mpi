# MPI Programming Guide

## Introduction to MPI

MPI (Message Passing Interface) is a standardized specification for message-passing communication in parallel computing. This guide covers the fundamental MPI concepts implemented and tested on this HPC cluster, using Python with the mpi4py library.

## MPI Concepts Overview

### Communicator

A communicator defines a group of processes that can communicate with each other. The default communicator, MPI.COMM_WORLD, includes all processes in the MPI job.

### Rank

Each process in a communicator has a unique identifier called its rank, numbered from 0 to size-1.

### Size

The total number of processes in a communicator.

### Basic Program Structure

```python
from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

print(f"Hello from rank {rank} of {size}")
```

## Point-to-Point Communication

### Send and Receive

The most basic MPI operations involve sending data from one process to another:

```python
from mpi4py import MPI
import numpy as np

comm = MPI.COMM_WORLD
rank = comm.Get_rank()

if rank == 0:
    data = np.array([1.0, 2.0, 3.0], dtype='d')
    comm.Send(data, dest=1, tag=0)
    print(f"Rank 0 sent: {data}")
elif rank == 1:
    data = np.empty(3, dtype='d')
    comm.Recv(data, source=0, tag=0)
    print(f"Rank 1 received: {data}")
```

### Sendrecv

The Sendrecv operation combines send and receive into a single call, preventing deadlocks:

```python
from mpi4py import MPI
import numpy as np

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# Ring topology: send to right, receive from left
left = (rank - 1) % size
right = (rank + 1) % size

send_data = np.array([rank * 10.0], dtype='d')
recv_data = np.empty(1, dtype='d')

# Send to right neighbor, receive from left neighbor
comm.Sendrecv(sendbuf=send_data, dest=right, sendtag=0,
              recvbuf=recv_data, source=left, recvtag=0)

print(f"Rank {rank}: sent {send_data[0]}, received {recv_data[0]}")
```

Important: In Sendrecv, the destination and source must be complementary. If sending to the right, receive from the left, and vice versa. Using the same neighbor for both causes deadlock.

### Ghost Cell Exchange

A common pattern in scientific computing is exchanging boundary data between neighboring processes:

```python
from mpi4py import MPI
import numpy as np

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

N = 10
local_grid = np.ones(N + 2, dtype='d') * rank

left = (rank - 1) % size
right = (rank + 1) % size

# Exchange boundaries
# Send left boundary to left neighbor, receive from right neighbor
comm.Sendrecv(sendbuf=local_grid[1:2], dest=left, sendtag=0,
              recvbuf=local_grid[-1:], source=right, recvtag=0)

# Send right boundary to right neighbor, receive from left neighbor
comm.Sendrecv(sendbuf=local_grid[-2:-1], dest=right, sendtag=1,
              recvbuf=local_grid[0:1], source=left, recvtag=1)

print(f"Rank {rank}: local_grid = {local_grid}")
```

## Collective Operations

Collective operations involve all processes in a communicator. They are optimized for efficiency and should be preferred over manual point-to-point implementations.

### Broadcast (Bcast)

One process sends the same data to all other processes:

```
Root (rank 0): [1, 2, 3, 4]
                   |
    +------+-------+-------+
    |      |       |       |
Rank 0  Rank 1  Rank 2  Rank 3
[1,2,3,4] [1,2,3,4] [1,2,3,4] [1,2,3,4]
```

```python
from mpi4py import MPI
import numpy as np

comm = MPI.COMM_WORLD
rank = comm.Get_rank()

if rank == 0:
    data = np.array([1.0, 2.0, 3.0, 4.0], dtype='d')
else:
    data = np.empty(4, dtype='d')

comm.Bcast(data, root=0)

print(f"Rank {rank}: data = {data}")
```

### Scatter

Root process divides data and sends pieces to all processes:

```
Root (rank 0): [1, 2, 3, 4, 5, 6, 7, 8]
                        |
        +-------+-------+-------+
        |       |       |       |
    Rank 0  Rank 1  Rank 2  Rank 3
    [1, 2]  [3, 4]  [5, 6]  [7, 8]
```

```python
from mpi4py import MPI
import numpy as np

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

if rank == 0:
    sendbuf = np.array([1, 2, 3, 4, 5, 6, 7, 8], dtype='d')
else:
    sendbuf = None

# Each process receives 2 elements
recvbuf = np.empty(2, dtype='d')

comm.Scatter(sendbuf, recvbuf, root=0)

print(f"Rank {rank}: received {recvbuf}")
```

Key points about Scatter:
- sendbuf is only needed on root process (can be None on others)
- recvbuf must be allocated on all processes
- sendbuf size must equal recvbuf size multiplied by number of processes

### Gather

Collects data from all processes to root (opposite of Scatter):

```
    Rank 0  Rank 1  Rank 2  Rank 3
    [0, 1]  [10,11] [20,21] [30,31]
        |       |       |       |
        +-------+-------+-------+
                    |
Root (rank 0): [0, 1, 10, 11, 20, 21, 30, 31]
```

```python
from mpi4py import MPI
import numpy as np

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# Each process has data to send
sendbuf = np.array([rank * 10, rank * 10 + 1], dtype='d')

# Only root needs receive buffer
if rank == 0:
    recvbuf = np.empty(2 * size, dtype='d')
else:
    recvbuf = None

comm.Gather(sendbuf, recvbuf, root=0)

if rank == 0:
    print(f"Root gathered: {recvbuf}")
```

Key points about Gather:
- sendbuf must be defined on all processes
- recvbuf only needed on root (can be None on others)
- recvbuf size must equal sendbuf size multiplied by number of processes

### Reduce

Combines values from all processes using an operation (sum, max, min, etc.):

```
    Rank 0  Rank 1  Rank 2  Rank 3
    [0, 0]  [1, 10] [2, 20] [3, 30]
        |       |       |       |
        +-------+-------+-------+
                   SUM
                    |
Root (rank 0): [6, 60]  (0+1+2+3=6, 0+10+20+30=60)
```

```python
from mpi4py import MPI
import numpy as np

comm = MPI.COMM_WORLD
rank = comm.Get_rank()

sendbuf = np.array([rank, rank * 10], dtype='d')

if rank == 0:
    recvbuf = np.empty(2, dtype='d')
else:
    recvbuf = None

comm.Reduce(sendbuf, recvbuf, op=MPI.SUM, root=0)

print(f"Rank {rank}: sent {sendbuf}")
if rank == 0:
    print(f"Root reduced (SUM): {recvbuf}")
```

Available reduction operations:
- MPI.SUM: Sum of all values
- MPI.MAX: Maximum value
- MPI.MIN: Minimum value
- MPI.PROD: Product of all values
- MPI.LAND: Logical AND
- MPI.LOR: Logical OR

### Allreduce

Like Reduce, but result is distributed to all processes:

```
    Rank 0  Rank 1  Rank 2  Rank 3
    [0, 0]  [1, 10] [2, 20] [3, 30]
        |       |       |       |
        +-------+-------+-------+
                   SUM
        +-------+-------+-------+
        |       |       |       |
    [6, 60] [6, 60] [6, 60] [6, 60]
```

```python
from mpi4py import MPI
import numpy as np

comm = MPI.COMM_WORLD
rank = comm.Get_rank()

sendbuf = np.array([rank, rank * 10], dtype='d')
recvbuf = np.empty_like(sendbuf)

comm.Allreduce(sendbuf, recvbuf, op=MPI.SUM)

print(f"Rank {rank}: sent {sendbuf}, result = {recvbuf}")
```

Allreduce is useful when all processes need the global result to continue computation, such as computing a global average for normalization.

## Complete Example Program

The following program demonstrates all collective operations:

```python
from mpi4py import MPI
import numpy as np

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# Step 1: Broadcast a parameter to all
if rank == 0:
    multiplier = np.array([10.0], dtype='d')
else:
    multiplier = np.empty(1, dtype='d')

comm.Bcast(multiplier, root=0)
print(f"Rank {rank}: received multiplier = {multiplier[0]}")

# Step 2: Scatter work data
chunk_size = 2
if rank == 0:
    sendbuf = np.arange(1, size * chunk_size + 1, dtype='d')
else:
    sendbuf = None

recvbuf = np.empty(chunk_size, dtype='d')
comm.Scatter(sendbuf, recvbuf, root=0)
print(f"Rank {rank}: received data = {recvbuf}")

# Step 3: Gather results
sendbuf_gather = np.array([rank * 10, rank * 10 + 1], dtype='d')

if rank == 0:
    recvbuf_gather = np.empty(chunk_size * size, dtype='d')
else:
    recvbuf_gather = None

comm.Gather(sendbuf_gather, recvbuf_gather, root=0)

if rank == 0:
    print(f"Root gathered: {recvbuf_gather}")

# Step 4: Reduce
sendbuf_reduce = np.array([rank, rank * 10], dtype='d')

if rank == 0:
    recvbuf_reduce = np.empty(2, dtype='d')
else:
    recvbuf_reduce = None

comm.Reduce(sendbuf_reduce, recvbuf_reduce, op=MPI.SUM, root=0)

if rank == 0:
    print(f"Root reduced (SUM): {recvbuf_reduce}")

# Step 5: Allreduce
sendbuf_allreduce = np.array([rank, rank * 10], dtype='d')
recvbuf_allreduce = np.empty_like(sendbuf_allreduce)

comm.Allreduce(sendbuf_allreduce, recvbuf_allreduce, op=MPI.SUM)
print(f"Rank {rank}: allreduce result = {recvbuf_allreduce}")

# Step 6: Local computation using scattered data
result = recvbuf * multiplier[0]
print(f"Rank {rank}: local_result = {result}")
```

## Running MPI Programs on the Cluster

### Interactive Execution

Set up the environment:

```bash
export PATH=/usr/lib64/openmpi/bin:$PATH
export LD_LIBRARY_PATH=/usr/lib64/openmpi/lib:$LD_LIBRARY_PATH
export OMPI_MCA_btl_tcp_if_include=10.10.10.0/24
```

Run across specific nodes:

```bash
mpiexec --host srv-hpc-02:2,srv-hpc-03:2 -n 4 python3 mpi_program.py
```

The :2 after each hostname specifies the number of processes (slots) to run on that node.

### Batch Job Submission

Create a job script:

```bash
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

# Build hostfile from SLURM allocation
HOSTFILE=/tmp/hostfile_$SLURM_JOB_ID
for node in $(scontrol show hostnames $SLURM_JOB_NODELIST); do
    echo "$node slots=2"
done > $HOSTFILE

echo "=== Hostfile ==="
cat $HOSTFILE

# Run MPI program
mpiexec --hostfile $HOSTFILE -n 8 python3 /nfs/shared/mpi/mpi_program.py

rm -f $HOSTFILE
```

Submit the job:

```bash
sbatch mpi_job.sh
```

Monitor job status:

```bash
squeue
```

View results:

```bash
cat mpi_output_*.log
```

## Buffer Management

### NumPy Arrays as Buffers

MPI operations require properly allocated buffers. Use NumPy arrays with explicit dtype:

```python
# Allocate empty buffer for receiving
recv_buffer = np.empty(10, dtype='d')

# Allocate buffer matching another array
recv_buffer = np.empty_like(send_buffer)

# Pre-initialized buffer
data = np.array([1.0, 2.0, 3.0], dtype='d')
```

### Common dtype Values

| dtype | Meaning          | Bytes |
|-------|------------------|-------|
| 'd'   | double (float64) | 8     |
| 'f'   | float (float32)  | 4     |
| 'i'   | int (int32)      | 4     |
| 'l'   | long (int64)     | 8     |

### Buffer Size Calculations

For Scatter:
- sendbuf size = chunk_size times number_of_processes
- recvbuf size = chunk_size

For Gather:
- sendbuf size = chunk_size
- recvbuf size = chunk_size times number_of_processes

## Common Pitfalls and Solutions

### Deadlock in Point-to-Point Communication

Problem: All processes call Send before Recv, causing deadlock.

Solution: Use Sendrecv or arrange sends and receives to avoid circular waiting:

```python
# Bad: potential deadlock
if rank == 0:
    comm.Send(data, dest=1)
    comm.Recv(data, source=1)
else:
    comm.Send(data, dest=0)
    comm.Recv(data, source=0)

# Good: using Sendrecv
comm.Sendrecv(send_data, dest=partner, recvbuf=recv_data, source=partner)
```

### Buffer Size Mismatch

Problem: MPI_ERR_TRUNCATE error when receive buffer is too small.

Solution: Ensure buffer sizes match the expected data:

```python
# Bad: buffer too small for 8 processes
recvbuf = np.empty(2, dtype='d')  # Only fits 2 elements
comm.Scatter(sendbuf, recvbuf, root=0)  # Each process needs 2 elements

# Good: correct buffer size
chunk_size = len(sendbuf) // size
recvbuf = np.empty(chunk_size, dtype='d')
```

### Wrong Network Interface

Problem: MPI tries to use wrong network, causing communication failures.

Solution: Specify the correct network:

```bash
export OMPI_MCA_btl_tcp_if_include=10.10.10.0/24
```

### Uninitialized Receive Buffers on Non-Root

Problem: Forgetting to allocate receive buffers on non-root processes for operations like Bcast.

Solution: Always allocate receive buffers on all processes:

```python
# Bad: only root has data
if rank == 0:
    data = np.array([1.0, 2.0], dtype='d')
comm.Bcast(data, root=0)  # Error on other ranks

# Good: all ranks have buffer
if rank == 0:
    data = np.array([1.0, 2.0], dtype='d')
else:
    data = np.empty(2, dtype='d')
comm.Bcast(data, root=0)
```

## Performance Considerations

### Minimize Communication

Collective operations are optimized but still involve overhead. Batch operations when possible:

```python
# Bad: multiple small broadcasts
comm.Bcast(param1, root=0)
comm.Bcast(param2, root=0)
comm.Bcast(param3, root=0)

# Good: single broadcast of combined data
if rank == 0:
    params = np.array([param1, param2, param3], dtype='d')
else:
    params = np.empty(3, dtype='d')
comm.Bcast(params, root=0)
```

### Use Collective Operations

Collective operations are optimized and outperform manual implementations:

```python
# Bad: manual reduction with point-to-point
if rank == 0:
    total = local_sum
    for i in range(1, size):
        temp = np.empty(1, dtype='d')
        comm.Recv(temp, source=i)
        total += temp
else:
    comm.Send(local_sum, dest=0)

# Good: use built-in Reduce
comm.Reduce(local_sum, total, op=MPI.SUM, root=0)
```

### Overlap Communication and Computation

When possible, use non-blocking operations to overlap communication with computation:

```python
# Start non-blocking receive
req = comm.Irecv(recv_buffer, source=neighbor)

# Do computation while waiting
result = compute_local_work()

# Wait for communication to complete
req.Wait()
```

## Summary of Collective Operations

| Operation | Direction  | Data Distribution        |
|-----------|------------|--------------------------|
| Bcast     | One to All | Same data to all         |
| Scatter   | One to All | Split data to each       |
| Gather    | All to One | Collect from each        |
| Reduce    | All to One | Combine with operation   |
| Allreduce | All to All | Combine and distribute   |
| Allgather | All to All | Collect from each to all |
| Alltoall  | All to All | Each sends piece to each |

This guide covers the fundamental MPI operations implemented and tested on the cluster. These patterns form the building blocks for more complex parallel algorithms.
