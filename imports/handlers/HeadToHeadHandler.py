from FixedUserRequestHandler import AutoVerifiedRequestHandler

import constants

from database.User import User

class HeadToHeadHandler(AutoVerifiedRequestHandler):
    def get(self):
        username = self.get_current_user()
        
        if username is None:
            self.validate_user()
            return
            
        user = User.get_user(username)
                
        if user.permission_level < constants.PERMISSION_LEVEL_USER:
            self.render("denied.html", user=user)
            return

        self.render("head-to-head.html", user=user)
