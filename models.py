from google.appengine.ext import db

class Category(db.Model):
    name = db.StringProperty()


class Wallet(db.Model):
    name = db.StringProperty()


class Transaction(db.Model):
    date = db.DateTimeProperty(auto_now_add=True)
    amount = db.IntegerProperty()
    category = db.ReferenceProperty(Category)
    wallet = db.ReferenceProperty(Wallet)
    source = db.ReferenceProperty(Wallet, collection_name='transfers')
    description = db.StringProperty()