import tornado.web
import constants

class FixedUserRequestHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_secure_cookie("user", "admin")
        self.redirect(constants.SERVICE_URL, permanent=False)

class AutoVerifiedRequestHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")

    def logout_user(self):
        self.clear_cookie("user")
        self.redirect("/logout", permanent=False)
        
    def validate_user(self):
        return

