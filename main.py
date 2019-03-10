"""Gnucash Scripts

Usage:
  main.py [options]

Options:
  -h --help                     Show this screen.
  --version                     Show version.
  --gnucash <gnucash>           Gnucash file.

"""

  #main.py ship new <name>...
  #main.py ship <name> move <x> <y> [--speed=<kn>]
  #main.py ship shoot <x> <y>
  #main.py mine (set|remove) <x> <y> [--moored | --drifting]

from docopt import docopt

import gnucash as gc
from gnucash import Session, Transaction, Split, GncNumeric

if __name__ == '__main__':
    args = docopt(__doc__)
    print(args)

    try:
        session = Session(args["--gnucash"])

    finally:
         session.end()


