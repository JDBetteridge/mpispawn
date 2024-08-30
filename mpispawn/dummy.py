from argparse import ArgumentParser

parser = ArgumentParser(
    prog='mpispawn',
    usage='',
    allow_abbrev=False,
    add_help=False,
    epilog='Enjoy!'
)
parser.add_argument(
    '-nW',
    # ~ '--nW',
    required=False,
    # ~ type=int,
    help='Size(s) of COMM_WORLD'
)
parser.add_argument(
    'command',
    metavar='command :',
    type=str,
    nargs='+',
    help='Command(s) to execute'
)

primary_parser = ArgumentParser(
    parents=[parser],
    allow_abbrev=False,
    add_help=False,
    conflict_handler='resolve'
)
primary_parser.add_argument(
    '--help',
    action='store_true',
    help='show this help message and exit'
)
primary_parser.add_argument(
    '-nW',
    required=True,
    # ~ nargs='*',
    # ~ type=int,
    help='Size(s) of COMM_WORLD(s)'
)


pargs, punk = primary_parser.parse_known_args()
args, unk = parser.parse_known_args()

print(vars(pargs), punk)
print(vars(args), unk)

primary_parser.print_help()
parser.print_help()
