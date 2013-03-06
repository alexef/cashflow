import jinja2
import json
import webapp2
from google.appengine.api import users

jinja_environment = jinja2.Environment()
jinja_environment.globals.update(
    {'uri_for': webapp2.uri_for,
     'logout_url': users.create_logout_url('/'),
     'user': users.get_current_user}
)


class BaseHandler(webapp2.RequestHandler):
    def render_to_response(self, template_name, context=None):
        template = jinja_environment.get_template(template_name)
        context = context or {}
        self.response.out.write(template.render(context))


class AuthenticatedBaseHandler(BaseHandler):
    def get_current_user(self):
        return users.get_current_user()

    def dispatch(self):
        self.user = self.get_current_user()
        if self.user is None:
            return self.redirect(users.create_login_url(self.request.uri))
        return super(AuthenticatedBaseHandler, self).dispatch()


class ApiHandler(AuthenticatedBaseHandler):
    def dispatch(self):
        result = super(ApiHandler, self).dispatch()
        if isinstance(result, (list, dict)):
            self.response.out.write(json.dumps(result))