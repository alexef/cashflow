import os
import webapp2
import jinja2
from google.appengine.ext import db
#from google.appengine.api import users

jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))
jinja_environment.globals.update(
    {'uri_for': webapp2.uri_for}
)


class Category(db.Model):
    name = db.StringProperty()


class Transaction(db.Model):
    date = db.DateTimeProperty(auto_now_add=True)
    amount = db.IntegerProperty()
    category = db.ReferenceProperty(Category)
    description = db.StringProperty()


class MainPage(webapp2.RequestHandler):
    def get(self):
        transactions = Transaction.all().order('-date')
        balance = sum([t.amount for t in transactions])
        template_values = {'transactions': transactions, 'categories': Category.all(),
                           'balance': balance}
        template = jinja_environment.get_template('index.html')
        self.response.out.write(template.render(template_values))


class AddTransaction(webapp2.RequestHandler):
    def post(self):
        amount = int(self.request.get('amount'))
        category = self.request.get('category')
        description = self.request.get('description')
        category_object = Category.gql("WHERE name = :1", category).get()
        transaction = Transaction(amount=amount, category=category_object, description=description)
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
        name = self.request.get('name')
        category = Category.gql("WHERE name = :1", name).get()
        if category is None:
            Category(name=name).put()
        self.get()

    def get(self):
        categories = Category.all()
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
