import os
import shlex
import sys

from argparse import ArgumentParser, ArgumentTypeError
from itertools import groupby

from mpi4py import MPI

# # Example invocations:
# mpispawn --check-spawn
# mpispawn -nU 8 -nW 2 python script.py
# mpispawn -nU 8 -nW 2 --print-commands python script.py
# mpispawn -nU 8 -nW 2 --wrapper python nonMPIscript.py
# mpispawn -nU 8 -nW 2 --wrapper --propagate_errcodes python nonMPIscript.py
# mpispawn -nU 10 -nW 1,2,3,4 python script.py
# mpispawn -nW 1,2,3,4 python script.py
# mpispawn -nW 1,2,3,4 python script_a.py : python script_b.py : python script_c.py : python script_d.py
# mpispawn -nW 1 python script_a.py : -nW 2 python script_b.py : -nW 3 python script_c.py : -nW 3 python script_d.py
#
# mpiexec -n 8 mpispawn -nW 4 script.py
# python -m mpispwan -nU 8 -nW 2 script.py
# mpiexec -n 8 python -m mpispawn -nW 2 script.py
#
# NOT ALLOWED:
# mpiexec -n 8 mpispawn -nW 4 python script_a.py : -nW 4 python script_b.py
# since the `:` is consumed by mpiexec.
# mpiexec -n 8 mpispawn -nW 4 python script_a.py : -n 4 python script_b.py
# This works but behaviour here might not be what you expect.
# `mpispawn` and `script_b.py` share a COMM_WORLD.
# `mpispawn` will spawn 2 instances of `script_a.py` over 2 COMM_WORLDs of size 4
#
# # Special environment variables
# MPISPAWN_UNIVERSE_SIZE
# MPISPAWN_WORLD_SIZE
# MPISPAWN_NUM_JOBS
# MPISPAWN_JOB_ID
#

# Parser for handling `--help` and `--check-spawn` only
short_circuit_parser = ArgumentParser(
    prog='???',
    usage='',
    allow_abbrev=False,
    add_help=False,
)
short_circuit_parser.add_argument(
    '--help',
    action='store_true',
    help='Show this help message and exit'
)
short_circuit_parser.add_argument(
    '--check-spawn',
    action='store_true',
    help='Verify whether it is possible to call MPI_comm_spawn'
)

# Parser for commands that are separated by `:` after `mpispawn`
parser = ArgumentParser(
    prog='mpispawn additional commands',
    usage='',
    allow_abbrev=False,
    add_help=False,
    epilog='Enjoy!'
)
parser.add_argument(
    '-nW',
    metavar='COMM_WORLD.size',
    required=False,
    type=int,
    help='Size of COMM_WORLD'
)
parser.add_argument(
    'command',
    metavar='command :',
    type=str,
    nargs='+',
    help='Command(s) to execute'
)

# Parser for `mpispawn` and the first provided command
primary_parser = ArgumentParser(
    prog='mpispawn',
    description='A command line tool to drive the MPI dynamic process management',
    epilog='subsequent commands:',
    allow_abbrev=False,
    add_help=False,
    conflict_handler='resolve'
)
primary_parser.add_argument(
    '--help',
    action='store_true',
    help='Show this help message and exit'
)
primary_parser.add_argument(
    '-nU',
    metavar='COMM_UNIVERSE.size',
    type=int,
    help='Size of COMM_UNIVERSE'
)
primary_parser.add_argument(
    '-nW',
    metavar='COMM_WORLD.size',
    required=True,
    help='Size(s) of COMM_WORLD(s)'
)
primary_parser.add_argument(
    'command',
    metavar='command :',
    type=str,
    nargs='+',
    help='Command(s) to execute'
)
primary_parser.add_argument(
    '--wrapper',
    action='store_true',
    help='Use a wrapper script around commands'
)
primary_parser.add_argument(
    '--propagate-errcodes',
    action='store_true',
    help='Return with the highest error code from spawned process'
)
primary_parser.add_argument(
    '--check-spawn',
    action='store_true',
    help='Verify whether it is possible to call MPI_comm_spawn'
)
primary_parser.add_argument(
    '--print-commands',
    action='store_true',
    help='Print the spawn commands formatted as a sequence of mpiexec commands without executing them'
)


def split_list(args, split=':'):
    '''Split a list into a list of sublists based on the `split` token.

    For example:
    ```
        split(['a', 'b', ':', 'c', 'd']) = [['a', 'b'], ['c', 'd']]
    ```
    Used here to separate multiple commands passed to `mpispawn` by splitting
    `sys.argv` on ':'
    '''
    return [list(x) for condition, x in groupby(args, lambda part: part != split) if condition]


def parse_all_args(args=sys.argv):
    '''Parse all of the commands and arguments passed to `mpispawn`.
    '''
    # Split all of the command line arguments by the `:` token
    parts = split_list(sys.argv)
    # Parse the arguments for `mpispawn` first (there are more of them)
    first_args, unk = primary_parser.parse_known_args(parts[0][1:])
    # Parse the arguments for the remaining commands
    subsequent_args = [parser.parse_known_args(a) for a in parts[1:]]

    # Establish the `COMM_WORLD.size`s from the `mpispawn` command
    try:
        Nworld = int(first_args.nW)
    except ValueError:
        try:
            Nworld = tuple(int(ii) for ii in first_args.nW.split(','))
        except ValueError:
            raise ArgumentTypeError(
                f'argument -nW: invalid value \'{first_args.nW}\' is not an int or tuple of ints'
            )

    # Establish the size of `MPI_UNIVERSE`
    # MPI.UNIVERSE_SIZE does not seem to contain the correct information
    Nuniverse = first_args.nU or MPI.COMM_WORLD.size
    if Nuniverse == 1:
        try:
            Nuniverse = os.environ['MPIEXEC_UNIVERSE_SIZE']
        except KeyError:
            raise ValueError('MPI Universe size is 1')

    first_args.nU = Nuniverse

    # Validate the `COMM_WORLD.size`s from the subsequent commands
    if isinstance(Nworld, tuple):
        if any(a[0].nW for a in subsequent_args):
            raise ArgumentTypeError(
                    'argument -nW: shouldn\'t be specified as a tuple and for each command'
                )
        first_args.nW = Nworld
    else:
        if subsequent_args and all(a[0].nW for a in subsequent_args):
            first_args.nW = [Nworld] + [a[0].nW for a in subsequent_args]
        elif subsequent_args and any(a[0].nW for a in subsequent_args):
            raise ArgumentTypeError(
                    'argument -nW: specified for some commands but not all'
                )
        else:
            k = Nuniverse//Nworld
            first_args.nW = [Nworld]*k

    # Check that the sum of the `COMM_WORLD.size`s is less than or equal to the MPI_UNIVERSE size
    if sum(first_args.nW) > first_args.nU:
        raise ArgumentTypeError(
            f'argument -nW: sum of `COMM_WORLD.size`s is {sum(first_args.nW)}, which is greater than MPI_UNIVERSE size {first_args.nU}'
        )

    # Create a list of commands the same length as the number of tasks
    Ntasks = len(first_args.nW)
    commands = [first_args.command + unk] + [a[0].command + a[1] for a in subsequent_args]
    if Ntasks > 1 and len(commands) == 1:
        # If there's only one command we repeat it to create multiple tasks
        commands *= Ntasks
    elif len(commands) != Ntasks:
        raise ArgumentTypeError(
            f'number of `COMM_WORLD.size`s: {Ntasks} is not equal to the number of commands: {len(commands)}'
        )
    first_args.command = commands

    return first_args


def print_commands(tasks):
    '''Print out the list of tasks as mpiexec commands.
    '''
    for n, command in tasks:
        print(f'mpiexec -n {n} {shlex.join(command)}')


def spawn(tasks, wrapper=False, errcodes=False):
    '''Spawn the list of tasks.
    '''
    # Collect the communicators
    comms = []

    # Spawn each task
    for ii, (n, command) in enumerate(tasks):
        if wrapper:
            cmd = sys.executable
            args = ['wrapper.py'] + command
        else:
            cmd = command[0]
            args = command[1:]
        error_code = [-1]*n
        comms.append(MPI.COMM_WORLD.Spawn(cmd, args, n, errcodes=error_code))
        if any(error_code):
            raise RuntimeError(f'Failed to execute {shlex.join(cmd + args)}')

    # Collect error codes
    status = os.EX_OK
    if MPI.COMM_WORLD.rank == 0 and (wrapper or errcodes):
        for comm in comms:
            spawn_status = comm.gather(None, root=MPI.ROOT)
            status = max([status, *spawn_status])

    return status


def main():
    # Handle `--help` and `--check-spawn` arguments
    args, unk = short_circuit_parser.parse_known_args()

    if args.help:
        # Just print help and return
        primary_parser.print_help()
        parser.print_help()
        retcode = os.EX_OK
    elif args.check_spawn:
        # Run a simple command in the wrapper and return
        retcode = spawn(
            [(1, ["echo", "Spawn successful"])],
            wrapper=True,
            errcodes=True
        )
    else:
        # Parse all of the command line arguments
        args = parse_all_args()
        from pprint import pprint
        pprint(vars(args))

        # Construct a list of tasks and associated `COMM_WORLD.size`s
        tasks = [*zip(args.nW, args.command)]

        if args.print_commands:
            # Just print out the list of commands as `mpiexec` lines
            print_commands(tasks)
            retcode = os.EX_OK
        else:
            # Spawn the collected tasks
            retcode = spawn(tasks, wrapper=args.wrapper, errcodes=args.propagate_errcodes)
            retcode = retcode if args.propagate_errcodes else os.EX_OK

    return retcode


if __name__ == '__main__':
    exit(main())
