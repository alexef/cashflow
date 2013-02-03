import os
import webapp2
import jinja2
from google.appengine.ext import db
from google.appengine.api import users
from models import Category, Wallet, Transaction


def get_account_ancestor(user):
    return db.Key.from_path('Account', user.nickname())


class MainPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user is None:
            return self.redirect(users.create_login_url(self.request.uri))
        transactions = Transaction.all().ancestor(get_account_ancestor(user)).order('-date')
        balance = sum([t.amount for t in transactions])
        template_values = {'transactions': transactions, 'categories': Category.all().ancestor(get_account_ancestor(user)),
                           'balance': balance, 'wallets': Wallet.all().ancestor(get_account_ancestor(user))}
        template = jinja_environment.get_template('index.html')
        self.response.out.write(template.render(template_values))


class WalletTransactions(webapp2.RequestHandler):
    def get(self, id):
        user = users.get_current_user()
        if user is None:
            return self.redirect(users.create_login_url(self.request.uri))
        wallet = Wallet.get_by_id(int(id), parent=get_account_ancestor(user))
        template_values = {'transactions': wallet.transaction_set,
                           'wallets': Wallet.all().ancestor(get_account_ancestor(user)),
                           'wallet': wallet,
                           'categories': Category.all().ancestor(get_account_ancestor(user)),
                           'balance': sum([t.amount for t in wallet.transaction_set]),
        }
        template = jinja_environment.get_template('wallet.html')
        self.response.out.write(template.render(template_values))


class WalletTransactionAdd(webapp2.RequestHandler):
    def post(self, id):
        user = users.get_current_user()
        if user is None:
            return self.redirect(users.create_login_url(self.request.uri))
        wallet = Wallet.get_by_id(int(id), parent=get_account_ancestor(user))
        amount = int(self.request.get('amount'))
        category = self.request.get('category')
        description = self.request.get('description')
        category_object = Category.gql("WHERE name = :1", category).get()
        transaction = Transaction(amount=amount, category=category_object, description=description,
                                  wallet=wallet, parent=get_account_ancestor(user))
        transaction.put()
        self.redirect(self.uri_for('wallet', id=wallet.key().id()))


class WalletsPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user is None:
            return self.redirect(users.create_login_url(self.request.uri))
        template = jinja_environment.get_template('wallets.html')
        self.response.out.write(template.render({'wallets': Wallet.all().ancestor(get_account_ancestor(user))}))

    def post(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
        name = self.request.get('name')
        wallet = Wallet.all().ancestor(get_account_ancestor(user)).filter('name', name).get()
        if wallet is None:
            Wallet(name=name, parent=get_account_ancestor(user)).put()
        self.get()


class AddTransaction(webapp2.RequestHandler):
    def post(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
        amount = int(self.request.get('amount'))
        category = self.request.get('category')
        description = self.request.get('description')
        category_object = Category.gql("WHERE name = :1", category).get()
        transaction = Transaction(amount=amount, category=category_object, description=description, parent=get_account_ancestor(user))
        transaction.put()
        self.redirect('/')


class TransactionDelete(webapp2.RequestHandler):
    def get(self, id):
        transaction = Transaction.get_by_id(int(id))
        template_values = {'object': transaction}
        template = jinja_environment.get_template('delete.html')
        self.response.out.write(template.render(template_values))

    def post(self, id):
        transaction = Transaction.get_by_id(int(id))
        transaction.delete()
        self.redirect(webapp2.uri_for('home'))


class CategoriesPage(webapp2.RequestHandler):
    def post(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
        name = self.request.get('name')
        category = Category.gql("WHERE ANCESTOR IS :1 AND name = :2", get_account_ancestor(user), name).get()
        if category is None:
            Category(name=name, parent=get_account_ancestor(user)).put()
        self.get()

    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
        categories = Category.all().ancestor(get_account_ancestor(user))
        template_values = {'categories': categories}
        template = jinja_environment.get_template('categories.html')
        self.response.out.write(template.render(template_values))


class CategoryPage(webapp2.RequestHandler):
    def get(self, category):
        category = Category.gql("WHERE name = :1", category).get()
        transactions = Transaction.gql("WHERE category = :1", category)
        template_values = {'category': category, 'transactions': transactions}
        template = jinja_environment.get_template('category.html')
        self.response.out.write(template.render(template_values))

    def post(self, category):
        category = Category.gql("WHERE name = :1", category).get()
        if category:
            category.name = self.request.get('name')
            category.put()
        self.redirect(webapp2.uri_for('category', category=category.name))


class CategoryDeletePage(webapp2.RequestHandler):
    def get(self, category):
        category = Category.gql("WHERE name = :1", category).get()
        template_values = {'object': category}
        template = jinja_environment.get_template('delete.html')
        self.response.out.write(template.render(template_values))

    def post(self, category):
        category = Category.gql("WHERE name = :1", category).get()
        if category:
            db.delete(category.transaction_set)
            category.delete()
        self.redirect(webapp2.uri_for('categories'))

jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))
jinja_environment.globals.update(
    {'uri_for': webapp2.uri_for, 'logout_url': users.create_logout_url('/'), 'user': users.get_current_user}
)

app = webapp2.WSGIApplication([
     webapp2.Route(r'/', handler=MainPage, name='home'),
     webapp2.Route(r'/wallet/', handler=WalletsPage, name='wallets'),
     webapp2.Route(r'/wallet/<id:\d+>/', handler=WalletTransactions, name='wallet'),
     webapp2.Route(r'/wallet/<id:\d+>/transaction/add/', handler=WalletTransactionAdd, name='wallet-transaction-add'),
     webapp2.Route(r'/transaction/add/', handler=AddTransaction, name='transaction-add'),
     webapp2.Route(r'/transaction/<id:\d+>/delete/', handler=TransactionDelete, name='transaction-del'),
     webapp2.Route(r'/categories', handler=CategoriesPage, name='categories'),
     webapp2.Route(r'/categories/<category:[^/]+>/', handler=CategoryPage, name='category'),
     webapp2.Route(r'/categories/<category:[^/]+>/delete/', handler=CategoryDeletePage, name='category-del'),
    ],
    debug=True)
