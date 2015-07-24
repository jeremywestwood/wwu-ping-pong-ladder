from FixedUserRequestHandler import AutoVerifiedRequestHandler
import json
import re

from sqlalchemy.sql.expression import desc, asc, label
import sqlalchemy.util._collections
from sqlalchemy import func

from database.SessionFactory import SessionFactory

from database.User import User
from database.Match import Match
from database.Score import Score
from database.Participation import Participation
from database.TrueSkillCache import TrueSkillCache

import constants

from resultdict import resultdict

def get_leaderboard_query(session):
    participation_matches = session.query( Participation.user_id.label("user_id"), 
                                           Match.id.label("match_id"), 
                                           Match.date_recorded.label("date") ).\
                            filter( Participation.match_id == Match.id ).subquery()
                            
    most_recent_match_date = session.query( participation_matches.c.user_id.label("user_id"),
                                            func.max(participation_matches.c.date).label("date") ).\
                            group_by( participation_matches.c.user_id ).subquery()
                            
    most_recent_matches = session.query( most_recent_match_date.c.user_id.label("user_id"),
                                         participation_matches.c.match_id.label("match_id"),
                                         most_recent_match_date.c.date.label("date") ).\
                            filter( most_recent_match_date.c.user_id == participation_matches.c.user_id ).\
                            filter( most_recent_match_date.c.date == participation_matches.c.date ).subquery()

    game_count = session.query( User.id.label("user_id"), 
                                func.count(Score.id).label("games") ).\
                            outerjoin( Score ).\
                            group_by( User.id ).subquery()

    game_winners = session.query(func.max(Score.score),Score.game_id.label('game_id'),
                                 Score.user_id.label('user_id')).group_by(Score.game_id).subquery()

    game_win_count = session.query( func.count(game_winners.c.game_id).label('wins'),
                                    game_winners.c.user_id.label("user_id") ).group_by(game_winners.c.user_id).subquery()

    most_recent_ratings = session.query( User.id.label("id"),
                                         User.displayname.label("displayname"),
                                         game_count.c.games.label("games"),
                                         TrueSkillCache.exposure.label("rating"),
                                         func.coalesce(game_win_count.c.wins,0).label('wins'),
                                         (func.coalesce(100*game_win_count.c.wins/game_count.c.games,0)).label("win_percentage")).\
                                                 outerjoin(game_win_count, User.id == game_win_count.c.user_id ).\
                            filter( User.id == game_count.c.user_id ).\
                            filter( User.id == most_recent_matches.c.user_id ).\
                            filter( User.id == TrueSkillCache.user_id ).\
                            filter( most_recent_matches.c.match_id == TrueSkillCache.match_id )

    return most_recent_ratings
"""
session = SessionFactory()
try:
    result = get_leaderboard_query(session).all()
            
    print resultdict(result)
finally:
    session.close()
                    
quit()
"""

sorting_expression = re.compile(r"sort\((?P<direction>[\+|\-])(?P<column>\w+)\)")
range_expression = re.compile(r"items=(?P<lower>\d+)-(?P<upper>\d+)")

class LeaderboardStore(AutoVerifiedRequestHandler):
    def get(self, user_id):
        username = self.get_current_user()
        
        if username is None:
            self.validate_user()
            return
            
        user = User.get_user(username)
                
        if user.permission_level < constants.PERMISSION_LEVEL_USER:
            self.render("denied.html", user=user)
            return
    
    
        if user_id is not None and user_id != "":
            # single item
            user_id = int(user_id)
            
            session = SessionFactory()
            try:
                result = get_leaderboard_query(session).filter(User.id == user_id).one()
                        
                result = resultdict(result)
                
                data = "{}&& "+json.dumps(result)
                self.set_header('Content-length', len(data))
                self.set_header('Content-type', 'application/json')
                self.write(data)
            finally:
                session.close()
        else:
            # query items
            
            raw_range = self.request.headers.get('Range', '')
            m = range_expression.match(raw_range)

            if m is not None:
                start = int(m.group('lower'))
                stop = int(m.group('upper')) + 1
            else:
                start = 0
                stop = -1

            raw_query = self.request.query
            m = sorting_expression.match(raw_query)
            
            if m is not None:
                    direction = m.group('direction')
                    column = m.group('column')
            else:
                    direction = '-'
                    column = "rating"
                    
            if column not in ["id", "displayname", "games", "wins", "win_percentage", "rating"]:
                column = "rating"

            if direction == '-':
                    direction = desc
            else:
                    direction = asc
            
            session = SessionFactory()
            try:
                query = get_leaderboard_query(session)
                        
                total = query.count()
            
                query = query.order_by(direction(column))
                        
                query = query.slice(start, stop)
                        
                result = query.all()

                result = resultdict(result)

                for i,res in enumerate(result,1):
                    res['order']= i
                data = "{}&& "+json.dumps(result)
                self.set_header('Content-range', 'items {}-{}/{}'.format(start, stop, total))
                self.set_header('Content-length', len(data))
                self.set_header('Content-type', 'application/json')
                self.write(data)
                
            finally:
                session.close()

