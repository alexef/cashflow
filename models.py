from google.appengine.ext import db


class Wallet(db.Model):
    name = db.StringProperty()


class Category(db.Model):
    name = db.StringProperty()


class Transaction(db.Model):
    date = db.DateTimeProperty(auto_now_add=True)
    amount = db.IntegerProperty()
    category = db.ReferenceProperty(Category)
    wallet = db.ReferenceProperty(Wallet)
    source = db.ReferenceProperty(Wallet, collection_name='transfers')
    description = db.StringProperty()


def get_account_ancestor(user):
    return db.Key.from_path('Account', user.nickname())