import calendar
import datetime
from google.appengine.ext import db
from models import Transaction, Wallet, Category, get_account_ancestor
from base import AuthenticatedBaseHandler


class MainHandler(AuthenticatedBaseHandler):
    def get_parent(self):
        return get_account_ancestor(self.user)


class MainPage(MainHandler):
    def get(self):
        transactions = Transaction.all().ancestor(self.get_parent()).order('-date')
        balance = sum([t.amount for t in transactions])
        template_values = {'transactions': transactions, 'categories': Category.all().ancestor(self.get_parent()),
                           'balance': balance, 'wallets': Wallet.all().ancestor(self.get_parent())}
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
        template_values = {'transactions': transactions,
                           'wallets': Wallet.all().ancestor(self.get_parent()),
                           'wallet': wallet,
                           'interval': (date_start, date_end),
                           'categories': Category.all().ancestor(self.get_parent()),
                           'balance': sum([t.amount for t in wallet.transaction_set]),
        }
        self.render_to_response('wallet.html', template_values)


class WalletTransactionAdd(MainHandler):
    def post(self, id):
        wallet = Wallet.get_by_id(int(id), parent=self.get_parent())
        amount = int(self.request.get('amount'))
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
        amount = int(self.request.get('amount'))
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
        transaction = Transaction.get_by_id(int(id))
        template_values = {'object': transaction}
        self.render_to_response('delete.html', template_values)

    def post(self, id):
        transaction = Transaction.get_by_id(int(id))
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
