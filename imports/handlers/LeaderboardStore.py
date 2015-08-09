from datetime import datetime
from sqlalchemy.orm import aliased
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
from database.FloatingTrophyCache import FloatingTrophyCache

import constants

from resultdict import resultdict

def get_leaderboard_query(session, at_date=None):
    participation_matches = session.query( Participation.user_id.label("user_id"), 
                                           Match.id.label("match_id"), 
                                           Match.date_recorded.label("date") ).\
                            filter( Participation.match_id == Match.id ).subquery()
                            
    most_recent_match_date = session.query( participation_matches.c.user_id.label("user_id"),
                                            func.max(participation_matches.c.date).label("date") ).\
                            group_by( participation_matches.c.user_id )

    if at_date is not None:
        most_recent_match_date = most_recent_match_date.filter(participation_matches.c.date < at_date)
    most_recent_match_date =most_recent_match_date.subquery()
                            
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
                    
            if column not in ["id", "displayname", "games", "wins", "win_percentage", "rating", "form", "streak",
                              'rank_change', 'order']:
                column = "rating"

            if direction == '-':
                    direction = 'desc'
            else:
                    direction = 'asc'
            
            session = SessionFactory()
            try:
                query = get_leaderboard_query(session)
                        
                total = query.count()
            
                # query = query.order_by(direction(column))
                        
                query = query.slice(start, stop)
                        
                result = query.all()

                result = resultdict(result)

                trophy_holder = session.query(FloatingTrophyCache).order_by(FloatingTrophyCache.id.desc()).first()

                today = datetime.now().date()
                today = datetime(today.year, today.month, today.day)
                today = int(today.strftime('%s'))

                previous_board = get_leaderboard_query(session, at_date = today).order_by(desc('rating')).all()
                previous_ranking = {}
                for pos, item in enumerate(previous_board,1):
                    previous_ranking[item.id] = (pos, item.rating)

                result = sorted(result, key= lambda k:k['rating'])[::-1]
                for i,res in enumerate(result,1):
                    res['order']= i
                    s1 = aliased(Score)
                    game_history = session.query(Score.score.label('player_score'), Score.game_id, s1.score.label('opponent_score') ).\
                        join(s1, sqlalchemy.and_(s1.game_id==Score.game_id, s1.user_id!=Score.user_id)).filter(Score.user_id==res['id']).\
                        order_by(Score.game_id.desc())
                    res['form'] = ''
                    game_history = ['W' if game.player_score>game.opponent_score else 'L' for game in game_history]
                    last_game = game_history[0]
                    opposite = 'W' if last_game == 'L' else 'L'
                    res['form'] = ''.join(reversed(game_history[0:5]))
                    res['streak'] = '%s%s' % (last_game, game_history.index(opposite) if  opposite in game_history else len(game_history))
                    res['rank_change'] = (previous_ranking[res['id']][0]- i) if previous_ranking.has_key(res['id']) else 0
                    res['rating_change'] = (res['rating']-previous_ranking[res['id']][1]) if previous_ranking.has_key(res['id']) else 0
                    res['hot_streak'] = False
                    res['trophy_holder'] = trophy_holder is not None and trophy_holder.user_id==res['id']

                result = sorted(result, key= sort_dict.get(column,lambda k:k[column]))
                if direction == 'desc':
                    result = result[::-1]

                best_streak = None

                for res in sorted(result, key= sort_dict.get('streak'))[::-1]:
                    if (best_streak is None and int(res['streak'][1:])>3) or res['streak'] == best_streak:
                        res['hot_streak'] = True
                        best_streak = res['streak']
                    else:
                        break

                data = "{}&& "+json.dumps(result)
                self.set_header('Content-range', 'items {}-{}/{}'.format(start, stop, total))
                self.set_header('Content-length', len(data))
                self.set_header('Content-type', 'application/json')
                self.write(data)
                
            finally:
                session.close()

sort_dict = {
    'streak': lambda k: int(('-' if k['streak'][0] == 'L' else '') + k['streak'][1:]),
    'form': lambda k: k['form'][::-1]
}