from FixedUserRequestHandler import AutoVerifiedRequestHandler

import constants

from database.User import User
from database.create_match import create_match, get_most_recent_ratings
from database.SessionFactory import SessionFactory

import datetime
import time
import json

class RecordMatchHandler(AutoVerifiedRequestHandler):
    def result(self, outcome, message):
        data = json.dumps({'type': outcome, 'msg': message})
        self.finish(data)
    
    def get(self, user1=None, user2=None):
        username = self.get_current_user()
        
        if username is None:
            self.validate_user()
            return
            
        user = User.get_user(username)

        if user.permission_level < constants.PERMISSION_LEVEL_USER:
            self.render("denied.html", user=user)
            return
        
        self.render("record-match.html", user=user, user1=user1, user2=user2)
        
    def post(self):
        username = self.get_current_user()
        
        if username is None:
            self.result("error", "Access denied.")
            return
            
        user = User.get_user(username)
                
        if user.permission_level < constants.PERMISSION_LEVEL_USER:
            self.result("error", "Access denied.")
            return
        
        try:
            user1_id = int(self.get_argument("userSelect1"))
            user2_id = int(self.get_argument("userSelect2"))
            # date_time = self.get_argument("date") + " " + self.get_argument("time")
            
            games = []
            for gnum in range(1):
                game = (int(self.get_argument("score_g{}_p0".format(gnum))), int(self.get_argument("score_g{}_p1".format(gnum))))
                games.append(game)
        except:
            self.result("error", "Invalid arguments. Check that all fields are filled out correctly.")
            return
        
        if user1_id == user2_id:
            self.result("error", "Opponents must be different users.")
            return

        if games[0][0] < 11 and games[0][1] < 11:
            self.result("error", "One score must be at least 11")
            return
        if abs(games[0][0]-games[0][1])<2:
            self.result("error", "Winner must win by 2")
            return
        if (games[0][0]<= 9 and games[0][1] >11) or (games[0][1]<= 9 and games[0][0] >11):
            self.result("error", "The winner should not have more than 11 if the loser has fewer than 10")
            return
        if games[0][0] >= 10 and games[0][1] >= 10 and abs(games[0][0]-games[0][1])>2:
            self.result("error", "Winner should only win by 2")
            return
        
        session = SessionFactory()
        try:
            user1 = session.query(User).filter(User.id == user1_id).one()
            user2 = session.query(User).filter(User.id == user2_id).one()
            
            # d = datetime.datetime.strptime(date_time, "%Y-%m-%d T%H:%M:%S")
            seconds = int(time.time()) #int(d.strftime('%s'))

            # filter out any games which have negative or all-zero scores
            games = filter(lambda g: all(map(lambda s: s >= 0, g)) and any(map(lambda s: s > 0, g)), games)
            
            if len(games) < 1:
                self.result("error", "A match consists of one or more games.")
                return
            current_score = (get_most_recent_ratings(user1.id).get('exposure',0), get_most_recent_ratings(user2.id).get('exposure',0))
            match = create_match(session, user1, user2, seconds, games)
            session.commit()
            new_score = (get_most_recent_ratings(user1.id).get('exposure',0), get_most_recent_ratings(user2.id).get('exposure',0))

            msg = "Match recorded successfully.<br><br>"\
            "Points Changes:<br>" \
            '%s: %0.3f<br>' \
            '%s: %0.3f' % (user1.displayname, new_score[0]-current_score[0], user2.displayname, new_score[1]-current_score[1])

            self.result("success", msg)
            
        finally:
            session.close()
