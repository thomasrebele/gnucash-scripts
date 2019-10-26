"""Gnucash Scripts

Usage:
  main.py [options] portfolio <tsv_file> [(checking <checking_root>)] [(invest <invest_root>)]
  main.py [options] statement <tsv_file> [(checking <checking_root>)]
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

import bs4
import time
from datetime import datetime
import requests
from decimal import Decimal
import gnucash as gc
from gnucash import Account, Session, Transaction, Split, GncNumeric, GncCommodity, GncPrice, ACCT_TYPE_STOCK

translation = {
    "Aktien": "Stock",
    "Fonds": "Fund",
    }

class CashScript:

    def __init__(self, session):
        self.session = session
        self.book = session.book
        self.root = self.book.get_root_account()
        self.commod_tab = self.book.get_table()
        self.price_db = self.book.get_price_db()

        self.currency_EUR = self.commod_tab.lookup('ISO4217', 'EUR')


    def find_account(self, path, account=None):
        if not account:
            account = self.root
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

    def find_transaction(self, account, date, desc, props={}):
        """Searches for the transaction in account with the specified date and description.
        Additional properties might be given which restricts the search.
        However, those are not obligatory.
        """

        account.SortSplits(True)
        splits = account.GetSplitList()
        candidates = []

        def check_split(split):
            """Returns true if the split corresponds to the constraints"""
            if date.date() != tx.GetDate().date() or desc != tx.GetDescription():
                return False

            for p_name, p_val in props.items():
                if p_name == "num":
                    split_val = split.GetParent().GetNum()
                    if split_val == "":
                        continue
                    if split_val != p_val:
                        return False

                if p_name == "value":
                    split_val = split.GetValue()
                    if split_val.num() * p_val.denom() != p_val.num() * split_val.denom():
                        return False

            return True

        for split in splits:
            tx = split.GetParent()
            if check_split(split):
                candidates.append(tx)

        if len(candidates) != 1:
            print("Could not find transaction " + str(desc) + " on " + str(date.date()) + " because there are " + str(len(candidates)) + " candidates")
            return None

        return candidates[0]

    def find_split_by_account(self, transaction, account):
        for split in transaction.GetSplitList():
            if split.GetAccount().get_full_name() == account.get_full_name():
                return split


    def tostring_account(self, account):
        if account:
            name = account.get_full_name()
            cmd = account.GetCommodity().get_fullname()
            if '.' in name:
                suffix = name[name.rindex('.')+1:]
                if suffix == cmd:
                    return name

            return name + " (" + cmd + ")"
        else:
            return "NO ACCOUNT FOUND"

    def print_account(self, account, prefix="   "):
        print(prefix + self.tostring_account(account))

    def print_split(self, split):
        account = split.GetAccount()
        print("split: "
            + "  " + self.tostring_account(account)
            + "  value: " + str(split.GetValue())
            + "  amount: " + str(split.GetAmount())
            + "  memo: " + split.GetMemo()
            + "  share price: " + str(split.GetSharePrice())
            + "  reconcile: " + str(split.GetReconcile())
            #+ "  action: " + split.GetAction()
            #+ "  base value: " + str(split.GetBaseValue(account.GetCommodity()))
            #+ "  balance: " + str(split.GetBalance())
            )

    def print_transaction(self, transaction):
        if not transaction:
            print("NO TRANSACTION")
            return
        print("Transaction on " + str(transaction.GetDate()) + ": " + str(transaction.GetDescription()) + " (" + str(transaction.GetNum()) + ")")

        fmt = [
            ("{:80}", "account", lambda s: self.tostring_account(s.GetAccount())),
            ("{:>20}", "value", lambda s: s.GetValue()),
            ("{:>20}", "amount", lambda s: s.GetAmount()),
            ("{:>25}", "share price", lambda s: s.GetSharePrice()),
            ("{:>7}", "rec.", lambda s: s.GetReconcile()),
            ("{:>20}", "memo", lambda s: s.GetMemo()),
            ]

        print("".join([f.format(h) for (f, h, _) in fmt]))

        for split in transaction.GetSplitList():
            acc = self.tostring_account(split.GetAccount())
            s = "  "
            for f in fmt:
                s += f[0].format(str(f[2](split)))
            print(s)
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

    def goc_stock_commodity(self, isin, name=None, namespace=None):
        # lookup onvista, e.g.  https://www.onvista.de/LU1737652583
        # parse first part of URL
        # commodity mnemonic needs to be unique for namespace

        if not name:
            name = isin

        if not namespace:
            namespace = "UNKNOWN"

        # 'book', 'fullname', 'commodity_namespace', 'mnemonic', 'cusip', and 'fraction'
        new_commod = GncCommodity(self.book, name, namespace, isin, isin, 1000)
        return self.commod_tab.insert(new_commod)


    def goc_stock_account(self, parent, isin, account_type):
        acc = self.find_account_by_isin(parent, isin)
        if acc:
            print("found " + str(acc.get_full_name()) + ", type: " + str(acc.GetType()))
            return acc

        # find type
        url = "https://onvista.de/" + isin
        r = requests.get(url)
        parts = r.url.split("/")[3:]

        namespace = parts[0].title()
        namespace = translation.get(namespace, namespace)
        fullname = "-".join(parts[1].split("-")[:-2])

        # create account
        stock_type = namespace
        category = parent.lookup_by_name(stock_type)
        if not category:
            category = Account(self.book)
            category.SetName(stock_type)
            category.SetType(account_type)
            category.SetCommodity(self.currency_EUR)
            parent.append_child(category)

        commodity = self.goc_stock_commodity(isin, name=fullname, namespace=namespace)
        stock_acc = Account(self.book)
        stock_acc.SetName(fullname)
        stock_acc.SetCommodity(commodity)
        stock_acc.SetType(account_type)
        category.append_child(stock_acc)

        print("created " + stock_acc.get_full_name())
        return stock_acc

    def goc_split(self, transaction, account, value, amount):
        # search for existing split
        for split in transaction.GetSplitList():
            check = split.GetAccount().get_full_name() == account.get_full_name()
            check = check and split.GetAmount().num() * amount.denom() == amount.num() * split.GetAmount().denom()
            check = check and split.GetValue().num() * value.denom() == value.num() * split.GetValue().denom()

            if check:
                return split

        # create new split
        split = Split(self.book)
        split.SetParent(transaction)
        split.SetAccount(account)
        split.SetMemo("automatic")
        split.SetValue(value)
        split.SetAmount(amount)
        return split

    def goc_stock_split(self, transaction, account, stock_count, total_value_cents):
        amount = GncNumeric(int(stock_count*1000), 1000)
        value = GncNumeric(total_value_cents, 100)
        return self.goc_split(transaction, account, value, amount)


    def goc_EUR_split(self, transaction, account, cents):
        value = GncNumeric(cents, self.currency_EUR.get_fraction())
        amount = GncNumeric(cents, self.currency_EUR.get_fraction())
        return self.goc_split(transaction, account, value, amount)

    def goc_stock_price(self, commodity, cents, datetime_date):
        price = GncPrice(self.book)
        price.set_commodity(commodity)
        price.set_currency(self.currency_EUR)
        price.set_time64(datetime_date)
        price.set_value(GncNumeric(cents,100))
        self.price_db.add_price(price)

    def read_statement_transactions(self, tsv_file, giro_acc):
        with open(tsv_file) as f:
            for i, line in enumerate(f):
                print(line)
                if line.startswith("#"):
                    continue

                row = line.rstrip("\n").split("\t")
                print(row)

                date = row[0]
                description = row[4]
                num = row[5]
                value = row[9]
                cents = int(value.replace(",",""))

                datetime_date = datetime.fromisoformat(date)

                props = {"num": num, "value": GncNumeric(cents, self.currency_EUR.get_fraction())}
                tx = self.find_transaction(giro_acc, datetime_date, description, props)

                info = (" date: " + str(date)
                        + " desc: " + str(description)
                        + " num: " + str(num)
                        + " value: " + str(value))

                created_timestamp = None
                if tx:
                    print("  updating " + info)
                else:
                    print("  creating " + info)
                    tx = Transaction(self.book)
                    created_timestamp = datetime.now()

                tx.BeginEdit()
                if created_timestamp:
                    tx.SetDateEnteredSecs(created_timestamp)

                tx.SetCurrency(self.currency_EUR)
                tx.SetDate(datetime_date.day, datetime_date.month, datetime_date.year)
                tx.SetDescription(description)
                tx.SetNum(num)

                self.goc_EUR_split(tx, giro_acc, cents)
                tx.CommitEdit()

                self.print_transaction(tx)


    def read_portfolio_transactions(self, tsv_file, checking_root, invest_root):
        with open(tsv_file) as f:
            for i, line in enumerate(f):
                if i==0: continue

                if line.startswith("#"):
                    continue

                row = line.rstrip("\n").split("\t")
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

                stock_count = Decimal(nominal.replace(",","."))
                stock_price = Decimal(price.replace(",","."))
                stock_cents = int(stock_price * 100)
                total_stock_cents = int(stock_count * stock_price * 100)

                # parse date
                datetime_date = datetime.fromisoformat(date)

                # find accounts
                giro_acc = self.find_account_by_number(checking_root, acc_number)
                assets_acc = self.goc_stock_account(invest_root, isin, ACCT_TYPE_STOCK)
                fee_acc = self.find_account("Expenses.Services.Broker", self.root)
                currency_acc = self.find_account("Trading.CURRENCY.EUR", self.root)
                stock_commodity = assets_acc.GetCommodity()

                # find transaction
                # TODO: add props
                tx = self.find_transaction(giro_acc, datetime_date, transaction_info)

                if not tx:
                    print("ERROR: transaction not found for " + line)
                    print("transaction info: " + str(transaction_info))
                    continue

                self.goc_stock_price(stock_commodity, stock_cents, datetime_date)

                # find split with the spent money
                sp_giro = self.find_split_by_account(tx, giro_acc)

                if not sp_giro:
                    raise "ERROR: split not found"


                tx.BeginEdit()

                # broker_expenses
                total_cents = sp_giro.GetValue().num()
                expenses_cents = abs(abs(total_cents) - abs(total_stock_cents))
                if expenses_cents > 0:
                    self.goc_EUR_split(tx, fee_acc, expenses_cents)

                self.goc_stock_split(tx, assets_acc, stock_count, total_stock_cents)

                for split in tx.GetSplitList():
                    if "Imbalance" in split.GetAccount().get_full_name():
#                        split.Destroy()
                        split.SetAccount(currency_acc)
                        value = GncNumeric(total_stock_cents, self.currency_EUR.get_fraction())
                        split.SetAmount(value)
                        split.SetValue(value)


                tx.CommitEdit()

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
            checking_root_path = args["<checking_root>"] or "Assets.Current Assets.Checking Account"
            invest_root_path = args["<invest_root>"] or "Assets.Investments"
            checking_root = cs.find_account(checking_root_path, root)
            invest_root = cs.find_account(invest_root_path, root)
            cs.read_portfolio_transactions(args["<tsv_file>"], checking_root, invest_root)

        if args["statement"]:
            checking_root_path = args["<checking_root>"] or "Assets.Current Assets.Checking Account"
            checking_root = cs.find_account(checking_root_path, root)
            cs.read_statement_transactions(args["<tsv_file>"], checking_root)


        # print(dir(root))
        # cs.print_accounts(root)

        session.save()
    finally:
        session.end()


