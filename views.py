from google.appengine.ext import db
from models import Transaction, Wallet, Category, get_account_ancestor
from base import AuthenticatedBaseHandler


class MainPage(AuthenticatedBaseHandler):
    def get(self):
        transactions = Transaction.all().ancestor(get_account_ancestor(self.user)).order('-date')
        balance = sum([t.amount for t in transactions])
        template_values = {'transactions': transactions, 'categories': Category.all().ancestor(get_account_ancestor(self.user)),
                           'balance': balance, 'wallets': Wallet.all().ancestor(get_account_ancestor(self.user))}
        self.render_to_response('index.html', template_values)


class WalletTransactions(AuthenticatedBaseHandler):
    def get(self, id):
        wallet = Wallet.get_by_id(int(id), parent=get_account_ancestor(self.user))
        template_values = {'transactions': wallet.transaction_set,
                           'wallets': Wallet.all().ancestor(get_account_ancestor(self.user)),
                           'wallet': wallet,
                           'categories': Category.all().ancestor(get_account_ancestor(self.user)),
                           'balance': sum([t.amount for t in wallet.transaction_set]),
                           }
        self.render_to_response('wallet.html', template_values)


class WalletTransactionAdd(AuthenticatedBaseHandler):
    def post(self, id):
        wallet = Wallet.get_by_id(int(id), parent=get_account_ancestor(self.user))
        amount = int(self.request.get('amount'))
        category = self.request.get('category')
        description = self.request.get('description')
        category_object = Category.gql("WHERE name = :1", category).get()
        transaction = Transaction(amount=amount, category=category_object, description=description,
            wallet=wallet, parent=get_account_ancestor(self.user))
        transaction.put()
        self.redirect(self.uri_for('wallet', id=wallet.id))


class WalletsPage(AuthenticatedBaseHandler):
    def get(self):
        self.render_to_response('wallets.html', {'wallets': Wallet.all().ancestor(get_account_ancestor(self.user))})

    def post(self):
        name = self.request.get('name')
        wallet = Wallet.all().ancestor(get_account_ancestor(self.user)).filter('name', name).get()
        if wallet is None:
            Wallet(name=name, parent=get_account_ancestor(self.user)).put()
        self.get()


class AddTransaction(AuthenticatedBaseHandler):
    def post(self):
        amount = int(self.request.get('amount'))
        category = self.request.get('category')
        description = self.request.get('description')
        category_object = Category.gql("WHERE name = :1", category).get()
        transaction = Transaction(amount=amount, category=category_object, description=description, parent=get_account_ancestor(self.user))
        transaction.put()
        self.redirect('/')


class TransactionDelete(AuthenticatedBaseHandler):
    def get(self, id):
        transaction = Transaction.get_by_id(int(id))
        template_values = {'object': transaction}
        self.render_to_response('delete.html', template_values)

    def post(self, id):
        transaction = Transaction.get_by_id(int(id))
        transaction.delete()
        self.redirect(self.uri_for('home'))


class CategoriesPage(AuthenticatedBaseHandler):
    def post(self):
        name = self.request.get('name')
        category = Category.gql("WHERE ANCESTOR IS :1 AND name = :2", get_account_ancestor(self.user), name).get()
        if category is None:
            Category(name=name, parent=get_account_ancestor(self.user)).put()
        self.get()

    def get(self):
        categories = Category.all().ancestor(get_account_ancestor(self.user))
        template_values = {'categories': categories}
        self.render_to_response('categories.html', template_values)


class CategoryPage(AuthenticatedBaseHandler):
    def get(self, id):
        category = Category.get_by_id(int(id), parent=get_account_ancestor(self.user))
        transactions = Transaction.gql("WHERE category = :1", category)
        template_values = {'category': category, 'transactions': transactions}
        self.render_to_response('category.html', template_values)

    def post(self, id):
        category = Category.get_by_id(int(id), parent=get_account_ancestor(self.user))
        if category:
            category.name = self.request.get('name')
            category.put()
        self.redirect(self.uri_for('category', id=category.id))


class CategoryDeletePage(AuthenticatedBaseHandler):
    def get(self, category):
        category = Category.gql("WHERE name = :1", category).get()
        template_values = {'object': category}
        self.render_to_response('delete.html', template_values)

    def post(self, category):
        category = Category.gql("WHERE name = :1", category).get()
        if category:
            db.delete(category.transaction_set)
            category.delete()
        self.redirect(self.uri_for('categories'))
