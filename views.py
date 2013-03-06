from StringIO import StringIO
import calendar
import datetime
from google.appengine.api import urlfetch, taskqueue
from google.appengine.ext import db
from models import Transaction, Wallet, Category, get_account_ancestor
from base import AuthenticatedBaseHandler, ApiHandler
from utils import UnicodeReader


class ParentMixin(object):
    def get_parent(self):
        return get_account_ancestor(self.user)


class MainHandler(AuthenticatedBaseHandler, ParentMixin):
    pass


class HomeRedirect(MainHandler):
    def get(self):
        #wallet = Wallet.all().ancestor(self.get_parent()).order('name').get()
        wallets = list(Wallet.all().ancestor(self.get_parent()))
        wallets.sort(key=lambda w: w.name)
        wallet = wallets[0]
        if wallet is None:
            self.redirect(self.uri_for('wallets'))
        else:
            self.redirect(self.uri_for('wallet', id=wallet.id))


class MainPage(MainHandler):
    def get(self):
        ts = Transaction.all().ancestor(self.get_parent())
        base_ts = Transaction.all(projection=('amount',)).ancestor(self.get_parent())
        balance = sum([t.amount for t in base_ts])
        transactions = ts.order('-date').fetch(50)
        template_values = {'transactions': transactions, 'categories': Category.all().ancestor(self.get_parent()),
                           'balance': balance,
                           'wallets': Wallet.all().ancestor(self.get_parent())}
        self.render_to_response('index.html', template_values)


class WalletTransactions(MainHandler):
    def get(self, id):
        today = datetime.date.today()
        date_start = self.request.GET.get('start', None)
        if date_start:
            date_start = datetime.datetime.strptime(date_start, '%Y-%m-%d').date()
        else:
            date_start = datetime.date(today.year, today.month, 1)
        date_end = self.request.GET.get('end', None)
        if date_end:
            date_end = datetime.datetime.strptime(date_end, '%Y-%m-%d').date()
        else:
            date_end = datetime.date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
        wallet = Wallet.get_by_id(int(id), parent=self.get_parent())
        transactions = wallet.transaction_set.filter('date >=', date_start).filter('date <=', date_end)
        nav = {}
        nav['previous'] = {'end': date_start - datetime.timedelta(days=1)}
        nav['previous']['start'] = datetime.date(nav['previous']['end'].year, nav['previous']['end'].month, 1)
        nav['next'] = {'start': date_end + datetime.timedelta(days=1)}
        nav['next']['end'] = datetime.date(nav['next']['start'].year, nav['next']['start'].month, calendar.monthrange(nav['next']['start'].year, nav['next']['start'].month)[1])
        nav['this'] = {'start': datetime.date(today.year, today.month, 1)}
        template_values = {'transactions': transactions,
                           'wallets': Wallet.all().ancestor(self.get_parent()),
                           'wallet': wallet,
                           'interval': (date_start, date_end),
                           'categories': Category.all().ancestor(self.get_parent()),
                           'balance': sum([t.amount for t in wallet.transaction_set]),
                           'nav': nav,
        }
        self.render_to_response('wallet.html', template_values)


class WalletTransactionAdd(MainHandler):
    def post(self, id):
        wallet = Wallet.get_by_id(int(id), parent=self.get_parent())
        amount = float(self.request.get('amount'))
        category = self.request.get('category')
        description = self.request.get('description')
        category_object = Category.gql("WHERE name = :1", category).get()
        transaction = Transaction(amount=amount, category=category_object, description=description,
            wallet=wallet, parent=self.get_parent())
        transaction.put()
        self.redirect(self.uri_for('wallet', id=wallet.id))


class WalletsPage(MainHandler):
    def get(self):
        self.render_to_response('wallets.html', {'wallets': Wallet.all().ancestor(self.get_parent())})

    def post(self):
        name = self.request.get('name')
        wallet = Wallet.all().ancestor(self.get_parent()).filter('name', name).get()
        if wallet is None:
            Wallet(name=name, parent=self.get_parent()).put()
        self.get()


class TransactionAdd(MainHandler):
    def post(self):
        amount = float(self.request.get('amount'))
        category = self.request.get('category')
        wallet = self.request.get('wallet')
        description = self.request.get('description')
        category_object = Category.gql("WHERE name = :1", category).get()
        wallet_object = Wallet.gql("WHERE name = :1", wallet).get()
        transaction = Transaction(amount=amount, category=category_object,
            wallet=wallet_object, description=description,
            parent=self.get_parent())
        transaction.put()
        self.redirect('/')


class TransactionDelete(MainHandler):
    def get(self, id):
        transaction = Transaction.get_by_id(int(id), parent=self.get_parent())
        template_values = {'object': transaction}
        self.render_to_response('delete.html', template_values)

    def post(self, id):
        transaction = Transaction.get_by_id(int(id), parent=self.get_parent())
        if transaction:
            transaction.delete()
        self.redirect(self.uri_for('home'))


class CategoriesPage(MainHandler):
    def post(self):
        name = self.request.get('name')
        category = Category.gql("WHERE ANCESTOR IS :1 AND name = :2", self.get_parent(), name).get()
        if category is None:
            Category(name=name, parent=self.get_parent()).put()
        self.get()

    def get(self):
        categories = Category.all().ancestor(self.get_parent())
        template_values = {'categories': categories}
        self.render_to_response('categories.html', template_values)


class CategoryPage(MainHandler):
    def get(self, id):
        category = Category.get_by_id(int(id), parent=self.get_parent())
        template_values = {'category': category, 'transactions': category.transaction_set}
        self.render_to_response('category.html', template_values)

    def post(self, id):
        category = Category.get_by_id(int(id), parent=self.get_parent())
        if category:
            category.name = self.request.get('name')
            category.put()
        self.redirect(self.uri_for('category', id=category.id))


class CategoryDeletePage(MainHandler):
    def get(self, id):
        category = Category.get_by_id(int(id), parent=self.get_parent())
        template_values = {'object': category}
        self.render_to_response('delete.html', template_values)

    def post(self, id):
        category = Category.get_by_id(int(id), parent=self.get_parent())
        if category:
            db.delete(category.transaction_set)
            category.delete()
        self.redirect(self.uri_for('categories'))


class ImportPage(MainHandler):
    def get(self):
        self.render_to_response('import.html')

    def post(self):
        taskqueue.add(url=self.uri_for('import-worker'), params={'user': self.user, 'url': self.request.get('url', None)})
        self.redirect(self.uri_for('import'))


class ImportWorker(MainHandler):
    def get_current_user(self):
        name = self.request.get('user')
        class FakeUser:
            name = ''
            def nickname(self):
                return self.name
        user = FakeUser()
        user.name = name
        return super(ImportWorker, self).get_current_user() or user

    def post(self):
        url = self.request.get('url', None)
        if not url:
            return
        # cache cats and ws
        cats = {}
        ws = {}
        for c in Category.all().ancestor(self.get_parent()):
            cats[c.name] = c
        for w in Wallet.all().ancestor(self.get_parent()):
            ws[w.name] = w
        result = urlfetch.fetch(url)
        if result.status_code == 200:
            fin = StringIO(result.content)
            r = UnicodeReader(fin)
            r.next()

            for line in r:
                date, amount, category, description, wallet = line
                date = datetime.datetime.strptime(date, '%Y-%m-%d')
                amount = float(amount)
                wallet = wallet[1:] if wallet.startswith('@') else wallet
                # category and wallet
                if category not in cats:
                    category = Category(parent=self.get_parent(), name=category)
                    category.put()
                    cats[category.name] = category
                else:
                    category = cats[category]
                if wallet not in ws:
                    wallet = Wallet(parent=self.get_parent(), name=wallet)
                    wallet.put()
                    ws[wallet.name] = wallet
                else:
                    wallet = ws[wallet]

                # Now add
                Transaction(parent=self.get_parent(), date=date, amount=amount, category=category, wallet=wallet, description=description).put()

        # done


class FlushDatabase(MainHandler):
    def get(self):
        self.render_to_response('delete.html', {'object': None, 'delete_message': 'all transactions'})

    def post(self):
        db.delete(Transaction.all(keys_only=True).ancestor(self.get_parent()))
        self.redirect(self.uri_for('home'))


# Api views
class ApiTransactions(ParentMixin, ApiHandler):
    def get(self, id):
        today = datetime.date.today()
        date_start = self.request.GET.get('start', None)
        if date_start:
            date_start = datetime.datetime.strptime(date_start, '%Y-%m-%d').date()
        else:
            date_start = datetime.date(today.year, today.month, 1)
        date_end = self.request.GET.get('end', None)
        if date_end:
            date_end = datetime.datetime.strptime(date_end, '%Y-%m-%d').date()
        else:
            date_end = datetime.date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
        wallet = Wallet.get_by_id(int(id), parent=self.get_parent())
        transactions = wallet.transaction_set.filter('date >=', date_start).filter('date <=', date_end)
        # Group by categories
        categories_plus = {}
        categories_mins = {}
        for t in transactions:
            if t.amount > 0:
                categories_plus[t.category.name] = categories_plus.get(t.category.name, 0) + t.amount
            else:
                categories_mins[t.category.name] = categories_mins.get(t.category.name, 0) + t.amount
        income = [(k, v) for k, v in categories_plus.iteritems()]
        outcome = [(k, v) for k, v in categories_mins.iteritems()]
        income.sort(key=lambda a:a[1])
        outcome.sort(key=lambda a:a[1], reverse=True)
        return {'income': income, 'outcome': outcome}