import subprocess
import sys

from mpi4py import MPI


def wrapper():
    """Thin wrapper to instantiate MPI and handle return codes"""
    comm = MPI.Comm.Get_parent()

    out = subprocess.run(sys.argv[1:])

    if comm != MPI.COMM_NULL:
        comm.gather(out.returncode, root=0)
        comm.Disconnect()

    return out.returncode


if __name__ == '__main__':
    exit(wrapper())
