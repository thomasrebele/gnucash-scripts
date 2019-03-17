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

import time
import datetime
from decimal import Decimal
import gnucash as gc
from gnucash import Account, Session, Transaction, Split, GncNumeric, GncCommodity, GncPrice

class CashScript:

    def __init__(self, session):
        self.session = session
        self.book = session.book
        self.root = self.book.get_root_account()
        self.commod_tab = self.book.get_table()
        self.price_db = self.book.get_price_db()

        commodity = self.goc_stock_commodity("DE000A0JBPG2")
        self.currency_EUR = self.commod_tab.lookup('ISO4217', 'EUR')

        # TODO: move to right place
        price = GncPrice(self.book)
        print(dir(price))
        price.set_commodity(commodity)
        price.set_currency(self.currency_EUR)
        millis = datetime.datetime(2199,4,1)
        price.set_time64(millis)
        price.set_value(GncNumeric(123,100))
        price.set_source_string("TODO")
        self.price_db.add_price(price)


    def find_account(self, path, account):
        if type(path) == str:
            path = path.split(".")
        child_account = account.lookup_by_name(path[0])
        if child_account is None or child_account.get_instance() is None:
            raise Exception("Account " + str(path) + " not found")
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

    def find_split_by_account(self, transaction, account):
        for split in transaction.GetSplitList():
            if split.GetAccount().get_full_name() == account.get_full_name():
                return split


    def print_account(self, account, prefix="   "):
        if account:
            print(prefix + account.get_full_name())
        else:
            print(prefix + "NO ACCOUNT FOUND")

    def print_split(self, split):
        self.print_account(split.GetAccount(), prefix="split for ")
        print("  value: " + str(split.GetValue())
            + "  amount: " + str(split.GetAmount())
            + "  memo: " + split.GetMemo())
        print()

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
        new_commod = GncCommodity(self.book, isin, name, isin, isin, 1)
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
            category.SetCommodity(self.currency_EUR)
            parent.append_child(category)

        # TODO account type
        commodity = self.goc_stock_commodity(isin)
        stock_acc = Account(self.book)
        stock_acc.SetName(isin)
        stock_acc.SetCommodity(commodity)
        category.append_child(stock_acc)
        return stock_acc

    #def goc_split(tx

    def goc_split(self, transaction, account, value, amount):
        split = Split(self.book)
        split.SetParent(transaction)
        split.SetAccount(account)
        split.SetValue(value)
        split.SetAmount(amount)
        split.SetMemo("automatic")
        return split

    def goc_stock_split(self, transaction, account, stock_count, value_cents):
        value = GncNumeric(value_cents, self.currency_EUR.get_fraction())
        amount = GncNumeric(stock_count, 1)
        return self.goc_split(transaction, account, value, amount)


    def goc_EUR_split(self, transaction, account, cents):
        value = GncNumeric(cents, self.currency_EUR.get_fraction())
        amount = GncNumeric(cents, self.currency_EUR.get_fraction())
        return self.goc_split(transaction, account, value, amount)

    def read_portfolio_transactions(self, csv_file, assets_account, trading_account):
        with open(csv_file, "r", encoding="iso-8859-1") as f:
            id_to_acc = {}


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

                stock_count = int(nominal.replace(",000",""))
                stock_price = Decimal(price.replace(",","."))
                total_stock_cents = int(stock_price * stock_count * 100)

                if not nominal.endswith(",000"):
                    raise "ERROR: only integer amount of stocks allowed"

                # find accounts
                giro_acc = self.find_account_by_number(assets_account, acc_number)
                trading_acc = self.goc_stock_account(trading_account, isin)
                assets_acc = self.goc_stock_account(assets_account, isin)
                currency_acc = self.find_account("CURRENCY.EUR", trading_account)
                fee_acc = self.find_account("Expenses.Services.Broker", self.root)

                # find transaction
                tx = giro_acc.FindTransByDesc(transaction_info)

                if not tx:
                    print("ERROR: transaction not found for " + line)
                    continue

                print("BEFORE --------------------------------------------------------------------------------")
                self.print_transaction(tx)

                # find split with the spent money
                sp_giro = self.find_split_by_account(tx, giro_acc)

                if not sp_giro:
                    raise "ERROR: split not found"

                total_cents = sp_giro.GetValue().num()

                tx.BeginEdit()
                # transfer stocks from virtual account to assets account
                self.goc_stock_split(tx, assets_acc, stock_count, total_stock_cents)
                self.goc_stock_split(tx, trading_acc, -stock_count, -total_stock_cents)
                # transfer virtual money to counterbalance the valueof the stocks
                #self.goc_EUR_split(tx, currency_acc, total_stock_cents)
                test_acc = self.find_account("Trading.CURRENCY.EUR", self.root)
                self.goc_EUR_split(tx, test_acc, total_stock_cents)

                # broker_expenses
                expenses_cents = abs(total_cents) - abs(total_stock_cents)
                print("total " + str(total_cents)
                        + " stock " + str(total_stock_cents)
                        + " exp " + str(expenses_cents))
                self.goc_EUR_split(tx, fee_acc, expenses_cents)

                tx.CommitEdit()

                print("AFTER --------------------------------------------------------------------------------")
                self.print_transaction(tx)




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


