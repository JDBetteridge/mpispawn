# mpispawn
A command line tool for launching multiple MPI jobs simultaneously.
The syntax is deliberately similar to that of `mpiexec`, but uses `MPI_Comm_spawn` to launch tasks on several separated `MPI_COMM_WORLD`s.
Most of the code is written in Python and relies upon the [mpi4py](https://github.com/mpi4py/mpi4py) library.

## Example invocations:
There are many different ways to call `mpispawn` in order to try to be as flexible as possible.

0. To check whether MPI_Comm_spawn can be called on your system at all (see caveats below), execute:
```bash
mpispawn --check-spawn
```

The `-nU` MPI universe size and `-nW` MPI_COMM_WORLD size parameters control the number of tasks and processes launched.
For consistency we will refer to a **task** as a group of processes all running over the same `MPI_COMM_WORLD` and we will refer to a **process** as a single execution thread running on an MPI rank.

1. Launch `script.py` over 4 copies of `MPI_COMM_WORLD` (launch 4 tasks) each of size 2, for a total of 8 processes:
```bash
mpispawn -nU 8 -nW 2 python script.py
```
The script `script.py` must call `MPI_Init()` or if using mpi4py, must have `from mpi4py import MPI` or equivalent.


2. The same as above, but rather than execute the command, print out a list of `mpiexec` statements roughly equivalent to what `mpispawn` will run:
```bash
mpispawn -nU 8 -nW 2 --print-commands python script.py
```

3. The same as 1, but the maximum value return code of any of the 8 processes is returned as the return code for `mpispawn`
```bash
mpispawn -nU 8 -nW 2 --propagate_errcodes python script.py
```

4. The same as 1, but uses a wrapper script to encapsulate a non-MPI script:
```bash
mpispawn -nU 8 -nW 2 --wrapper python nonMPIscript.py
```

5. Create a universe of size 10 and 4 tasks with `MPI_COMM_WORLD` sizes of 1, 2, 3 and 4 respectively:
```bash
mpispawn -nU 10 -nW 1,2,3,4 python script.py
```
Specifying both `-nU 10` and `-nW 1,2,3,4` is redundant, but explicit. Note that there cannot be spaces between the `MPI_COMM_WORLD` sizes as they would be split up as separate arguments on the command line.

6. The same as 5, but not specifying the universe size:
```bash
mpispawn -nW 1,2,3,4 python script.py
```

7. Create 4 tasks with `MPI_COMM_WORLD` sizes of 1, 2, 3 and 4 to run 4 different scripts `script_[a-d].py` respectively:
```bash
mpispawn -nW 1,2,3,4 python script_a.py : python script_b.py : python script_c.py : python script_d.py
```

8. The same as 7, but specifying the `MPI_COMM_WORLD` size in each command section separately:
```bash
mpispawn -nW 1 python script_a.py : -nW 2 python script_b.py : -nW 3 python script_c.py : -nW 3 python script_d.py
```
This is similar to the MPMD syntax of `mpiexec`.

### Other invocations
```bash
mpiexec -n 8 mpispawn -nW 4 script.py
```

```bash
python -m mpispwan -nU 8 -nW 2 script.py
```

```bash
mpiexec -n 8 python -m mpispawn -nW 2 script.py
```

### Bad ideas
Since `mpispawn` uses the colon character (`:`) to separate tasks in the same way that `mpiexec` uses `:` to separate tasks for launching MPMD jobs the following does not work:
```bash
mpiexec -n 8 mpispawn -nW 4 python script_a.py : -nW 4 python script_b.py
```
since the `:` is consumed by `mpiexec` and `mpiexec` doesn't understand the `-nW` argument.

You can launch a job as:
```bash
mpiexec -n 8 mpispawn -nW 4 python script_a.py : -n 4 python script_b.py
```
This works but behaviour here might not be what you expect:
 - `mpispawn` and `script_b.py` share an `MPI_COMM_WORLD`.
 - `mpispawn` will spawn 2 instances of `script_a.py` over 2 `MPI_COMM_WORLD`s of size 4

## Special environment variables
It is often the case that arguments corresponding to the universe or world size, the number of tasks being launched, or the ID of a task within the universe is required by the underlying script.
The following environment variables are set only inside the spawned task:
- `\$MPISPAWN_UNIVERSE_SIZE` - The size of the MPI universe.
- `\$MPISPAWN_WORLD_SIZE` - The size of the MPI_COMM_WORLD for the given task.
- `\$MPISPAWN_NUM_TASKS` - The total number of tasks spawned by `mpispawn`.
- `\$MPISPAWN_TASK_ID0` - The ID of the task within the universe, indexed from 0.
- `\$MPISPAWN_TASK_ID1` - The ID of the task within the universe, indexed from 1. (Because some people prefer to start counting from 1)

Note that the dollar character (`$`) must be excaped inside the `mpispawn` call on the command line.
This is because otherwise `bash` will expand the environment vairable before handing control to `mpispawn`.

## Motivation
This tool was inspired by the need to launch multiple independent `MPI_COMM_WOLRD` tasks simultaneously for testing.
It is possible with some MPI distributions to achieve this by nesting one `MPI_Init` call within another executable that has already called `MPI_Init`.
However, this is not condoned and indeed not supported by some MPI distributions.

What is supported is using `MPI_Comm_spawn` within an executable that has already called `MPI_Init`.
The spawned task is then allowed (indeed, it is _required_) to call `MPI_Init`.
`mpispawn` is designed to be a command line utility to expose this functionality in a way similar to `mpiexec` so the user doesn't have to set up their own scripts calling `MPI_Comm_spawn`.

The project is written in Python, becasue the author didn't fancy writing all of the argument parsing logic in C.

## Caveats
- `MPI_Comm_spawn` can be a bit flakey and support can be poor.
- Additionally HPC tool vendors may disable the functionality deliberately.
