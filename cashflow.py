import os
import webapp2
import jinja2

from views import *
from base import jinja_environment

jinja_environment.loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates'))

url_mappings = (
    webapp2.Route(r'/', handler=MainPage, name='home'),
    webapp2.Route(r'/wallet/', handler=WalletsPage, name='wallets'),
    webapp2.Route(r'/wallet/<id:\d+>/', handler=WalletTransactions, name='wallet'),
    webapp2.Route(r'/wallet/<id:\d+>/transaction/add/', handler=WalletTransactionAdd, name='wallet-transaction-add'),
    webapp2.Route(r'/transaction/add/', handler=TransactionAdd, name='transaction-add'),
    webapp2.Route(r'/transaction/<id:\d+>/delete/', handler=TransactionDelete, name='transaction-del'),
    webapp2.Route(r'/categories', handler=CategoriesPage, name='categories'),
    webapp2.Route(r'/categories/<id:\d+>/', handler=CategoryPage, name='category'),
    webapp2.Route(r'/categories/<id:\d+>/delete/', handler=CategoryDeletePage, name='category-del'),
    webapp2.Route(r'/import/', handler=ImportPage, name='import'),
    webapp2.Route(r'/import/worker/', handler=ImportWorker, name='import-worker'),
    webapp2.Route(r'/tools/flush/', handler=FlushDatabase, name='tools-flush'),
)

app = webapp2.WSGIApplication(url_mappings,  debug=True)
