import subprocess
import sys

import numpy as np
from mpi4py import MPI


def wrapper():
    """Thin wrapper to instantiate MPI and handle return codes"""
    comm = MPI.Comm.Get_parent()

    try:
        out = subprocess.run(sys.argv[1:])
        return_code = out.returncode
    except FileNotFoundError:
        return_code = 127

    if comm != MPI.COMM_NULL:
        buffer = np.empty((1,), dtype=np.int8)
        buffer[0] = return_code
        comm.Gather(buffer, None, root=0)
        comm.Disconnect()

    return return_code


if __name__ == '__main__':
    exit(wrapper())
