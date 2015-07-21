from FixedUserRequestHandler import AutoVerifiedRequestHandler

import constants

from database.User import User
from database.SessionFactory import SessionFactory

import datetime
import json

def create_user(session, username, displayname, email=None):
    """Creates and adds a user to the session given the details."""
    user = User(permission_level=1, username=username)
    user.displayname = displayname
    if email:
        user.email = email
    session.add(user)

class AddUserHandler(AutoVerifiedRequestHandler):
    def result(self, outcome, message):
        data = json.dumps({'type': outcome, 'msg': message})
        self.finish(data)
    
    def get(self):
        username = self.get_current_user()
        
        if username is None:
            self.validate_user()
            return
            
        user = User.get_user(username)
                
        if user.permission_level < constants.PERMISSION_LEVEL_ADMIN:
            self.render("denied.html", user=user)
            return
        
        self.render("add-user.html", user=user)
        
    def post(self):
        username = self.get_current_user()
        
        if username is None:
            self.result("error", "Access denied.")
            return
            
        user = User.get_user(username)
                
        if user.permission_level < constants.PERMISSION_LEVEL_ADMIN:
            self.result("error", "Access denied.")
            return
        
        try:
            username = self.get_argument("username")
            displayname = self.get_argument("displayname")
            email = self.get_argument("email", None) or None
        except:
            self.result("error", "Invalid arguments. Check that all fields are filled out correctly.")
            return
        
        session = SessionFactory()
        try:
            create_user(session, username, displayname, email)
            session.commit()
            
            self.result("success", "User added successfully.")
            
        finally:
            session.close()

