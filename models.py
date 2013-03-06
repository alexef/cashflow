from google.appengine.api import users
from google.appengine.ext import db


class BaseModel(db.Model):
    @property
    def id(self):
        return self.key().id()


class Wallet(BaseModel):
    name = db.StringProperty()
    active = db.BooleanProperty(default=True)


class Category(BaseModel):
    name = db.StringProperty()


class Transaction(BaseModel):
    date = db.DateTimeProperty(auto_now_add=True)
    amount = db.FloatProperty()
    category = db.ReferenceProperty(Category)
    wallet = db.ReferenceProperty(Wallet)
    source = db.ReferenceProperty(Wallet, collection_name='transfers')
    description = db.StringProperty()


def get_account_ancestor(user):
    return db.Key.from_path('Account', user.nickname())


class User(BaseModel):
    email = db.EmailProperty()
    admin = db.BooleanProperty(default=False)

    @classmethod
    def get_from_auth(cls, auth_user):
        user = cls.all().filter('email', auth_user.email()).get()
        if user is None:
            user = cls(email=auth_user.email())
            user.put()
            return user
        return user


def get_current_user():
    u = users.get_current_user()
    if u is None:
        return u
    u.profile = User.get_from_auth(u)
    return u