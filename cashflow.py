import os
import webapp2
import jinja2
from google.appengine.ext import db
from google.appengine.api import users

jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))
jinja_environment.globals.update(
    {'uri_for': webapp2.uri_for, 'logout_url': users.create_logout_url('/'), 'user': users.get_current_user}
)


class Category(db.Model):
    name = db.StringProperty()


class Transaction(db.Model):
    date = db.DateTimeProperty(auto_now_add=True)
    amount = db.IntegerProperty()
    category = db.ReferenceProperty(Category)
    description = db.StringProperty()


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
                           'balance': balance}
        template = jinja_environment.get_template('index.html')
        self.response.out.write(template.render(template_values))


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



app = webapp2.WSGIApplication(
    [webapp2.Route(r'/', handler=MainPage, name='home'),
     webapp2.Route(r'/add', handler=AddTransaction, name='transaction-add'),
     webapp2.Route(r'/transaction/<id:\d+>/delete/', handler=TransactionDelete, name='transaction-del'),
     webapp2.Route(r'/categories', handler=CategoriesPage, name='categories'),
     webapp2.Route(r'/categories/<category:[^/]+>/', handler=CategoryPage, name='category'),
     webapp2.Route(r'/categories/<category:[^/]+>/delete/', handler=CategoryDeletePage, name='category-del'),
    ],
    debug=True)
