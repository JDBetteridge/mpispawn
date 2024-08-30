import subprocess
import sys

from mpi4py import MPI


def wrapper():
    comm = MPI.Comm.Get_parent()

    print(f"Child process on {MPI.COMM_WORLD.size}")
    out = subprocess.run(sys.argv[1:])
    print(out.returncode)

    if comm != MPI.COMM_NULL:
        comm.gather(out.returncode, root=0)
        comm.Disconnect()

    return out.returncode


if __name__ == '__main__':
    exit(wrapper())
