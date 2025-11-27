"""Gnucash Scripts

Usage:
  main.py [options] portfolio <tsv_file> [(checking <checking_root>)] [(invest <invest_root>)]
  main.py [options] statement <tsv_file> [(checking <checking_root>)]
  main.py [options] ofx <ofx_file> [(checking <checking_root>)]

Options:
  -h --help                     Show this screen.
  --version                     Show version.
  --gnucash <gnucash>           Gnucash file.
  --heuristic                   Match statements based on their date and value only.

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
from collections import defaultdict

from ofxparse import ofxparse

translation = {
    "Aktien": "Stock",
    "Fonds": "Fund",
    }

class CashScript:

    def __init__(self, session, args):
        self.session = session
        self.args = args
        if session == None:
            return

        self.book = session.book
        self.root = self.book.get_root_account()
        self.commod_tab = self.book.get_table()
        self.price_db = self.book.get_price_db()

        self.currency_EUR = self.commod_tab.lookup('ISO4217', 'EUR')

        self.split_fmt = [
            ("{:80}", "account", lambda s: self.tostring_account(s.GetAccount())),
            ("{:>20}", "value", lambda s: s.GetValue()),
            ("{:>20}", "amount", lambda s: s.GetAmount()),
            ("{:>25}", "share price", lambda s: s.GetSharePrice()),
            ("{:>7}", "rec.", lambda s: s.GetReconcile()),
            ("{:>20}", "memo", lambda s: s.GetMemo()),
            ]


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

    def find_transaction(self, account, date, desc, props={}, idx=None, check_desc=True):
        """Searches for the transaction in account with the specified date and description.
        Additional properties might be given which restricts the search.
        However, those are not obligatory.
        """

        account.SortSplits(True)
        splits = account.GetSplitList()
        candidates = []

        def check_split(split, check_desc=True):
            """Returns true if the split corresponds to the constraints"""
            if date.date() != tx.GetDate().date():
                return False
            if check_desc and desc != tx.GetDescription():
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
            if check_split(split, check_desc=check_desc):
                candidates.append(tx)

        if idx == None:
            len_check = lambda candidates: len(candidates) == 1
            idx = 0
        else:
            len_check = lambda candidates: len(candidates) != 0

        if not len_check(candidates):
            print("Could not find transaction " + str(desc)
                    + " on " + str(date.date())
                    + " because there are " + str(len(candidates)) + " candidates")
            if len(candidates) == 0:
                return None
            return candidates

        if len(candidates) > 1:
            candidates.sort(key=lambda tx: int(tx.GetNum()))

        return candidates[idx]

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

    def print_split_row(self, split, prefix="  "):
        s = prefix
        for f in self.split_fmt:
            s += f[0].format(str(f[2](split)))
        print(s)

    def print_transaction(self, transaction):
        if not transaction:
            print("NO TRANSACTION")
            return
        print("Transaction on " + str(transaction.GetDate()) + ": " + str(transaction.GetDescription()) + " (" + str(transaction.GetNum()) + ")")

        print("".join([f.format(h) for (f, h, _) in self.split_fmt]))

        for split in transaction.GetSplitList():
            self.print_split_row(split)

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
            return acc

        # find type
        # url = "https://onvista.de/" + isin
        # r = requests.get(url)
        # parts = r.url.split("/")[3:]

        # namespace = parts[0].title()
        # namespace = translation.get(namespace, namespace)
        # fullname = "-".join(parts[1].split("-")[:-2])

        fullname = input("Please provide a name for " + str(isin) + " (e.g., by searching on finanzen.net): ").strip()
        namespace = input("Please provide the kind (Etf, Fund, Stock, etc): ").strip()

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
        """Search or create a split. Returns split, isNew."""
        # search for existing split
        for split in transaction.GetSplitList():
            check = split.GetAccount().get_full_name() == account.get_full_name()
            check = check and split.GetAmount().num() * amount.denom() == amount.num() * split.GetAmount().denom()
            check = check and split.GetValue().num() * value.denom() == value.num() * split.GetValue().denom()

            if check:
                return split, False

        # create new split
        split = Split(self.book)
        split.SetParent(transaction)
        split.SetAccount(account)
        split.SetMemo("automatic")
        split.SetValue(value)
        split.SetAmount(amount)
        return split, True

    def goc_stock_split(self, transaction, account, stock_count, total_value_cents):
        amount = GncNumeric(int(stock_count*1000), 1000)
        value = GncNumeric(total_value_cents, 100)
        return self.goc_split(transaction, account, value, amount)


    def goc_EUR_split(self, transaction, account, cents):
        value = GncNumeric(cents, self.currency_EUR.get_fraction())
        amount = GncNumeric(cents, self.currency_EUR.get_fraction())
        return self.goc_split(transaction, account, value, amount)

    def goc_stock_price(self, commodity, cents, datetime_date):
        # check whether entry already exists
        for price in self.price_db.get_prices(commodity, self.currency_EUR):
            check = price.get_time64() == datetime_date
            check = check and price.get_value().num == cents
            check = check and price.get_value().denom == 100
            if check:
                return price

        price = GncPrice(self.book)
        price.set_commodity(commodity)
        price.set_currency(self.currency_EUR)
        price.set_time64(datetime_date)
        price.set_value(GncNumeric(cents,100))
        self.price_db.add_price(price)
        return price

    def read_ofx_transactions(self, ofx_file):
        with open(ofx_file) as fileobj:
            ofx = ofxparse.OfxParser.parse(fileobj)

        acc = ofx.account
        # TODO: find/create account
        print(acc)
        for d in dir(acc):
            x = getattr(acc, d)
            if " at 0x" in repr(x):
                continue
            print(str(d) + "  " + str(x))


    def read_statement_transactions(self, tsv_file, giro_acc):
        with open(tsv_file) as f:
            for i, line in enumerate(f):
                try:
                    self.read_statement_transaction_line(giro_acc, line)
                except Exception as e:
                    raise RuntimeError("Problem in line " + str(i+1) + " of " + str(tsv_file) + ": " + line) from e

    def read_statement_transaction_line(self, giro_acc, line):
        if line.startswith("#"):
            return
        row = line.rstrip("\n").split("\t")

        date = row[0]
        description = row[4]
        num = row[5]
        value = row[7]
        cents = int(value.replace(",",""))

        try:
            datetime_date = datetime.fromisoformat(date)
        except Exception as e:
            print("Ignoring record because of erroneous date: " + str(date))
            return

        props = {"num": num, "value": GncNumeric(cents, self.currency_EUR.get_fraction())}
        check_desc = not ("--heuristic" in self.args and self.args["--heuristic"])
        tx = self.find_transaction(giro_acc, datetime_date, description, props, check_desc=check_desc)

        if type(tx) == list:
            print("ERROR: Multiple candidates, ignoring")
            return

        created_timestamp = None
        updated = False
        if not tx:
            tx = Transaction(self.book)
            created_timestamp = datetime.now()

        tx.BeginEdit()
        if created_timestamp:
            tx.SetDateEnteredSecs(created_timestamp)

        tx.SetDate(datetime_date.day, datetime_date.month, datetime_date.year)
        tx.SetDescription(description)
        if not tx.GetCurrency() or tx.GetCurrency().get_unique_name() != self.currency_EUR.get_unique_name():
            updated = True
            tx.SetCurrency(self.currency_EUR)
        if tx.GetNum() != num:
            updated = True
            tx.SetNum(num)

        split, isNew = self.goc_EUR_split(tx, giro_acc, cents)
        if created_timestamp or updated or isNew:
            info = (" date: " + str(date)
                + " desc: " + str(description)
                + " num: " + str(num)
                + " value: " + str(value))
            if created_timestamp:
                print("  creating " + info)
            else:
                print("  updating " + info)
            self.print_split_row(split, prefix="       ")
        tx.CommitEdit()


    def read_portfolio_transactions(self, tsv_file, checking_root, invest_root):
        with open(tsv_file) as f:
            # count how many transactions we have seen on the same day with the same description
            tx_to_id = defaultdict(lambda: 0)

            for i, line in enumerate(f):
                if line.startswith("#"):
                    continue
                try:
                    self.read_portfolio_transaction_line(tsv_file, checking_root, invest_root, line, tx_to_id)
                except Exception as e:
                    raise RuntimeError("Problem in line " + str(i+1) + " of " + str(tsv_file) + ": " + line) from e


    def read_portfolio_transaction_line(self, tsv_file, checking_root, invest_root, line, tx_to_id):
        row = line.rstrip("\n").split("\t")

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

        if total_stock_cents == 0 or "Dividendenzahlung" in transaction_info:
            print("WARNING: ignoring " + str(line.rstrip("\n")))
            return

        if "Lagerstellenwechsel" in transaction_info:
            print("WARNING: ignoring " + str(line.rstrip("\n")))
            return

        if "WP-Ausbuchung" in transaction_info:
            print("WARNING: ignoring " + str(line.rstrip("\n")))
            return

        if "Spin Off in" in transaction_info:
            print("WARNING: ignoring " + str(line.rstrip("\n")))
            return


        # parse date
        datetime_date = datetime.fromisoformat(date)

        # find accounts
        giro_acc = self.find_account_by_number(checking_root, acc_number)
        assets_acc = self.goc_stock_account(invest_root, isin, ACCT_TYPE_STOCK)
        fee_acc = self.find_account("Expenses.Services.Broker", self.root)
        currency_acc = self.find_account("Trading.CURRENCY.EUR", self.root)
        stock_commodity = assets_acc.GetCommodity()

        # find transaction
        key = (datetime_date.date(), transaction_info)
        tx = self.find_transaction(giro_acc, datetime_date, transaction_info, idx=tx_to_id[key])
        tx_to_id[key] += 1

        if not tx or type(tx) == list:
            print("ERROR: transaction not found for " + line)
            print("transaction info: " + str(transaction_info))
            return

        self.goc_stock_price(stock_commodity, stock_cents, datetime_date)

        # find split with the spent money
        sp_giro = self.find_split_by_account(tx, giro_acc)

        if not sp_giro:
            raise "ERROR: split not found"

        updated = False
        tx.BeginEdit()

        # broker_expenses
        total_cents = sp_giro.GetValue().num()
        expenses_cents = abs(abs(total_cents) - abs(total_stock_cents))
        if expenses_cents > 0:
            _, isNew = self.goc_EUR_split(tx, fee_acc, expenses_cents)
            updated |= isNew

        _, isNew = self.goc_stock_split(tx, assets_acc, stock_count, total_stock_cents)
        updated |= isNew
        value = GncNumeric(total_stock_cents, self.currency_EUR.get_fraction())
        _, isNew = self.goc_split(tx, currency_acc, value, value)
        updated |= isNew

        tx.CommitEdit()

        if updated:
            print()
            print("  imported " + line)
            self.print_transaction(tx)




if __name__ == '__main__':
    args = docopt(__doc__)
    print(args)

    session = None
    try:
        if args["--gnucash"]:
            session = Session(args["--gnucash"])
            book = session.book
            root = book.get_root_account()
        cs = CashScript(session, args)

        def find_acc(args, key, default):
            acc_path = args[key] or default
            return cs.find_account(acc_path, root)

        def find_checking(args):
            return find_acc(args, "<checking_root>", "Assets.Current Assets.Checking Account")

        if args["portfolio"]:
            checking_root = find_checking(args)
            invest_root = find_acc(args, "<invest_root>", "Assets.Investments")
            cs.read_portfolio_transactions(args["<tsv_file>"], checking_root, invest_root)

        if args["statement"]:
            checking_root = find_checking(args)
            cs.read_statement_transactions(args["<tsv_file>"], checking_root)

        if args["ofx"]:
            checking_root = find_checking(args)
            cs.read_ofx_transactions(args["<ofx_file>"])


        # print(dir(root))
        # cs.print_accounts(root)

        if session: session.save()
    finally:
        if session: session.end()


