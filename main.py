"""Gnucash Scripts

Usage:
  main.py [options] portfolio <csv_file> [assets <assets_account>] [trading <trading_account>]
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
        self.commod_tab = self.book.get_table()


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
        if account.GetCommodity() and account.GetCommodity().get_cusip() == isin:
            return account
        for child in account.get_children():
            found = self.find_account_by_isin(child, isin)
            if found:
                return found

    def find_account_by_number(self, account, number):
        if number in account.GetDescription():
            return account
        for child in account.get_children():
            found = self.find_account_by_number(child, number)
            if found:
                return found



    def print_account(self, account, prefix="   "):
        if account:
            print(prefix + account.get_full_name())
        else:
            print(prefix + "NO ACCOUNT FOUND")

    def print_split(self, split):
        self.print_account(split.GetAccount(), prefix="split for ")
        print("  memo: " + split.GetMemo())
        print("  value: " + str(split.GetValue()))
        print("  amount: " + str(split.GetAmount()))

    def print_transaction(self, transaction):
        if not transaction:
            print("NO TRANSACTION")
            return
        for split in transaction.GetSplitList():
            self.print_split(split)
        pass

    def print_accounts(self, account, prefix="  "):
        self.print_account(account, prefix)
        for child in account.get_children():
            self.print_accounts(child, prefix+"  ")

    def print_account_info(self, account):
        commodity = account.GetCommodity()

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

    def print_transactions(self, account):
        # TODO: use description to find transaction
        pass
        #for split in account.GetSplitList():
        #    self.print_split(split)

    def goc_stock_commodity(self, isin):
        # lookup onvista, e.g.  https://www.onvista.de/LU1737652583
        # parse first part of URL
        # commodity mnemonic needs to be unique for namespace

        # 'book', 'fullname', 'commodity_namespace', 'mnemonic', 'cusip', and 'fraction'
        name = isin # TODO
        new_commod = GncCommodity(book, isin, name, isin, isin, 1)
        return self.commod_tab.insert(new_commod)


    def goc_stock_account(self, parent, isin):
        acc = self.find_account_by_isin(parent, isin)
        if acc:
            return acc

        # create account
        stock_type = "TODO"
        category = parent.lookup_by_name(stock_type)
        if not category:
            category = Account(self.book)
            category.SetName(stock_type)
            currency = self.commod_tab.lookup('ISO4217', 'EUR')
            category.SetCommodity(currency)
            parent.append_child(category)

        # TODO account type
        commodity = self.goc_stock_commodity(isin)
        stock_acc = Account(self.book)
        stock_acc.SetName(isin)
        stock_acc.SetCommodity(commodity)
        category.append_child(stock_acc)
        return stock_acc

    #def goc_split(trans


    def read_portfolio_transactions(self, csv_file, assets_account, trading_account):
        with open(csv_file, "r", encoding="iso-8859-1") as f:
            id_to_acc = {}

            currency_acc = self.find_account("CURRENCY.EUR", trading_account)
            currency = currency_acc.GetCommodity()

            for i, line in enumerate(f):
                if i==0: continue

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

                # find accounts
                giro_acc = self.find_account_by_number(assets_account, acc_number)
                trading_acc = self.goc_stock_account(trading_account, isin)
                assets_acc = self.goc_stock_account(assets_account, isin)

                # find transaction
                trans = giro_acc.FindTransByDesc(transaction_info)
                self.print_transaction(trans)

                if not trans:
                    print("ERROR: transaction not found for " + line)
                    continue

                print(dir(trans))
                total = "TODO: LOOKUP SPLIT FOR giro_acc"
                amount = GncNumeric(100 * -1, currency.get_fraction())
                value = GncNumeric(100 * -1, currency.get_fraction())
                #self.goc_split(trans, currency_acc, value, amount)






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
            cs.print_account(assets_acc)
            trading_acc = cs.find_account(trading_path, root)
            cs.read_portfolio_transactions(args["<csv_file>"], assets_acc, trading_acc)

        # print(dir(root))
        # cs.print_accounts(root)

        session.save()
    finally:
        session.end()


