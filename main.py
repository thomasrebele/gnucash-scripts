"""Gnucash Scripts

Usage:
  main.py [options]

Options:
  -h --help                     Show this screen.
  --version                     Show version.
  --gnucash <gnucash>           Gnucash file.
  --portfolio <portfolio>       Portfolio transactions.

"""

  #main.py ship new <name>...
  #main.py ship <name> move <x> <y> [--speed=<kn>]
  #main.py ship shoot <x> <y>
  #main.py mine (set|remove) <x> <y> [--moored | --drifting]

from docopt import docopt

import gnucash as gc
from gnucash import Session, Transaction, Split, GncNumeric, GncCommodity

def find_account(account, path):
    if type(path) == str:
        path = path.split(".")
    child_account = account.lookup_by_name(path[0])
    if child_account is None or child_account.get_instance() is None:
        raise Exception("Account " + str(relative_name) + " not found")
    if len(path) > 1:
        return find_account(child_account, path[1:])
    return child_account


def print_accounts(account, prefix="  "):
    print(prefix + str(account.get_full_name()))
    for child in account.get_children():
        print_accounts(child, prefix+"  ")

def print_account_info(account):
    commodity = account.GetCommodity()
    print(dir(commodity))

    print("commodity:")
    print("  full name: " + str(commodity.get_fullname()))
    print("  default symbol: " + str(commodity.get_default_symbol()))
    print("  user symbol: " + str(commodity.get_user_symbol()))
    print("  namespace: " + str(commodity.get_namespace()))
    print("  namespace ds: " + str(commodity.get_namespace_ds()))
    print("  fraction: " + str(commodity.get_fraction()))
    print("  cusip: " + str(commodity.get_cusip()))
    print("  quote flag: " + str(commodity.get_quote_flag()))
    print("  quote source: " + str(commodity.get_quote_source()))
    print("  quote tz: " + str(commodity.get_quote_tz()))


def add_stock_commodity(isin):
    # lookup onvista, e.g.  https://www.onvista.de/LU1737652583
    # parse first part of URL
    # commodity mnemonic needs to be unique for namespace

    pass

def add_stock_transaction(account, commodity, price, count):
    pass


def read_portfolio_transactions(csv_file):
    with open(csv_file, "r", encoding="iso-8859-1") as f:
        for line in f:
            row = line.rstrip("\n").split(";")
            print(row)
            acc_number = row[0]
            date = row[1]
            valuta = row[2]
            isin = row[3]
            description = row[4]
            nominal = row[5]
            transaction_info = row[7]
            price = row[9]
            depot = row[10]

            print(nominal)



if __name__ == '__main__':
    args = docopt(__doc__)
    print(args)

    try:
        session = Session(args["--gnucash"])
        book = session.book
        root = book.get_root_account()


        commod_tab = book.get_table()

        # 'book', 'fullname', 'commodity_namespace', 'mnemonic', 'cusip', and 'fraction'
        new_commod = GncCommodity(book, "NAME1", "FundXYZ", "XYZ123x", "DE0007123a", 1)
        commod_tab.insert(new_commod)
        new_commod = GncCommodity(book, "NAME2", "FundABC", "XYZ123x", "DE0007123b", 1)
        commod_tab.insert(new_commod)
        new_commod = GncCommodity(book, "NAME3", "FundDEF", "XYZ123x", "DE0007123c", 1)
        commod_tab.insert(new_commod)
        print(dir(commod_tab))


        # print(dir(root))
        # print_accounts(root)

        session.save()

    finally:
        session.end()


