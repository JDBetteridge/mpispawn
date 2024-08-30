# mpispawn


## Example invocations:
mpispawn --check-spawn
mpispawn -nU 8 -nW 2 python script.py
mpispawn -nU 8 -nW 2 --print-commands python script.py
mpispawn -nU 8 -nW 2 --wrapper python nonMPIscript.py
mpispawn -nU 8 -nW 2 --wrapper --propagate_errcodes python nonMPIscript.py
mpispawn -nU 10 -nW 1,2,3,4 python script.py
mpispawn -nW 1,2,3,4 python script.py
mpispawn -nW 1,2,3,4 python script_a.py : python script_b.py : python script_c.py : python script_d.py
mpispawn -nW 1 python script_a.py : -nW 2 python script_b.py : -nW 3 python script_c.py : -nW 3 python script_d.py

mpiexec -n 8 mpispawn -nW 4 script.py
python -m mpispwan -nU 8 -nW 2 script.py
mpiexec -n 8 python -m mpispawn -nW 2 script.py

NOT ALLOWED:
mpiexec -n 8 mpispawn -nW 4 python script_a.py : -nW 4 python script_b.py
since the `:` is consumed by mpiexec.
mpiexec -n 8 mpispawn -nW 4 python script_a.py : -n 4 python script_b.py
This works but behaviour here might not be what you expect.
`mpispawn` and `script_b.py` share a COMM_WORLD.
`mpispawn` will spawn 2 instances of `script_a.py` over 2 COMM_WORLDs of size 4

## Special environment variables
MPISPAWN_UNIVERSE_SIZE
MPISPAWN_WORLD_SIZE
MPISPAWN_NUM_JOBS
MPISPAWN_JOB_ID
