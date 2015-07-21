from FixedUserRequestHandler import AutoVerifiedRequestHandler

import constants

from database.User import User
from database.Match import Match
from database.SessionFactory import SessionFactory

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.exc import MultipleResultsFound

class AdminHandler(AutoVerifiedRequestHandler):
    def get(self, mid=None):
        username = self.get_current_user()
        
        if username is None:
            self.validate_user()
            return
            
        user = User.get_user(username)
                
        if user.permission_level < constants.PERMISSION_LEVEL_ADMIN:
            self.render("denied.html", user=user)
            return
        
        self.render("admin.html", user=user)

