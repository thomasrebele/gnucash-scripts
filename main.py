"""Gnucash Scripts

Usage:
  main.py [options] portfolio <csv_file> assets <assets_account> [trading <trading_account>]
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
from gnucash import Account, Session, Transaction, Split, GncNumeric, GncCommodity

class CashScript:

    def __init__(self, session):
        self.session = session
        self.book = session.book
        self.root = self.book.get_root_account()


    def find_account(self, path, account):
        if type(path) == str:
            path = path.split(".")
        child_account = account.lookup_by_name(path[0])
        if child_account is None or child_account.get_instance() is None:
            raise Exception("Account " + str(relative_name) + " not found")
        if len(path) > 1:
            return self.find_account(path[1:], child_account)
        return child_account

    def find_account_by_isin(self, account, isin):
        if account.GetCommodity().get_cusip() == isin:
            return account
        for child in account.get_children():
            found = self.find_account_by_isin(child, isin)
            if found:
                return found


    def print_account(self, account, prefix="   "):
        if account:
            print(account.get_full_name())
        else:
            print("NO ACCOUNT FOUND")

    def print_accounts(self, account, prefix="  "):
        self.print_account(account, prefix)
        for child in account.get_children():
            self.print_accounts(child, prefix+"  ")

    def print_account_info(self, account):
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


    def add_stock_commodity(self, isin):
        # lookup onvista, e.g.  https://www.onvista.de/LU1737652583
        # parse first part of URL
        # commodity mnemonic needs to be unique for namespace

        pass

    def add_stock_transaction(self, account, commodity, price, count):
        pass

    def get_stock_account(self, root, isin):
        acc = self.find_account_by_isin(root, isin)
        if acc:
            return acc
        # TODO: create account
        # stock_type = "TODO"
        # category = Account()
        # print(dir(root))



    def read_portfolio_transactions(self, csv_file, assets_account, trading_account):
        with open(csv_file, "r", encoding="iso-8859-1") as f:
            id_to_acc = {}

            for line in f:
                row = line.rstrip("\n").split(";")
                print()
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

                print(isin)

                trading_acc = self.get_stock_account(trading_account, isin)
                assets_acc = self.get_stock_account(assets_account, isin)

                self.print_account(trading_acc)
                self.print_account(assets_acc)






if __name__ == '__main__':
    args = docopt(__doc__)
    print(args)

    try:
        session = Session(args["--gnucash"])
        cs = CashScript(session)
        book = session.book
        root = book.get_root_account()

        if args["portfolio"]:
            assets_path = args["<assets_account>"] or "Assets"
            trading_path = args["<trading_account>"] or "Trading"
            assets_acc = cs.find_account(assets_path, root)
            trading_acc = cs.find_account(trading_path, root)
            cs.read_portfolio_transactions(args["<csv_file>"], assets_acc, trading_acc)

        # commod_tab = book.get_table()

        # # 'book', 'fullname', 'commodity_namespace', 'mnemonic', 'cusip', and 'fraction'
        # new_commod = GncCommodity(book, "NAME3", "FundDEF", "XYZ123x", "DE0007123c", 1)
        # commod_tab.insert(new_commod)
        # print(dir(commod_tab))

        # print(dir(root))
        cs.print_accounts(root)

        session.save()
    finally:
        session.end()


