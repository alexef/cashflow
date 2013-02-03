import jinja2
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
        self.response.out.write(template.render(context))


class AuthenticatedBaseHandler(BaseHandler):
    def dispatch(self):
        self.user = users.get_current_user()
        if self.user is None:
            return self.redirect(users.create_login_url(self.request.uri))
        return super(AuthenticatedBaseHandler, self).dispatch()