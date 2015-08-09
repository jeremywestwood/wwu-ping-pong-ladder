from FixedUserRequestHandler import AutoVerifiedRequestHandler
import json
import re

from sqlalchemy.sql.expression import desc, asc, label
import sqlalchemy.util._collections
from sqlalchemy import func, and_, or_

from database.SessionFactory import SessionFactory

from database.User import User
from database.Match import Match
from database.Game import Game
from database.Score import Score
from database.Participation import Participation
from database.User import User

import constants

from resultdict import resultdict
    
def get_match_history_query(session, filter_user_id=None):

    #(game_id, score)

    winning_scores = session.query( Score.game_id, func.max(Score.score).label("score") ).\
                                group_by( Score.game_id ).subquery()
                            
    #(game_id, score)

    losing_scores = session.query( Score.game_id, func.min(Score.score).label("score") ).\
                               group_by( Score.game_id ).subquery()
                            
    #(match_id, user_id, games_won)
                            
    game_winners = session.query(   Game.match_id,
                                    Score.user_id, 
                                    func.count(winning_scores.c.game_id).label("games_won"),
                                    func.max(winning_scores.c.score).label("total_points"), ).\
                              filter(   Game.id == Score.game_id ).\
                              filter(   winning_scores.c.game_id == Score.game_id ).\
                              filter(   Score.score == winning_scores.c.score ).\
                              group_by(Game.match_id, Score.user_id).subquery()

    #(match_id, user_id, games_won)
                            
    game_losers = session.query(   Game.match_id,
                                   Score.user_id, 
                                   func.count(losing_scores.c.game_id).label("games_lost"),
                                   func.max(losing_scores.c.score).label("total_points"), ).\
                             filter(   Game.id == Score.game_id ).\
                             filter(   losing_scores.c.game_id == Score.game_id ).\
                             filter(   Score.score == losing_scores.c.score ).\
                             group_by(Game.match_id, Score.user_id).subquery()

    #(match_id, user_id, games_won)
    
    match_game_counts = session.query( Participation.match_id,
                                       Participation.user_id,
                                       func.coalesce(game_winners.c.games_won, 0).label("games_won"),
                                       func.coalesce(game_losers.c.games_lost, 0).label("games_lost"),
                                       func.coalesce(game_winners.c.total_points, 0).label("points_won"),
                                       func.coalesce(game_losers.c.total_points, 0).label("points_lost"),
                                     )
    match_game_counts = match_game_counts.\
                              outerjoin(game_winners, 
                                and_(game_winners.c.match_id == Participation.match_id, 
                                game_winners.c.user_id == Participation.user_id) ).\
                              outerjoin(game_losers, 
                                and_(game_losers.c.match_id == Participation.match_id, 
                                game_losers.c.user_id == Participation.user_id) ).\
                              subquery()
                                
    match_winners = session.query( match_game_counts.c.match_id, 
                                   match_game_counts.c.user_id, 
                                   User.displayname, 
                                   match_game_counts.c.games_won.label("games_won"),
                                   match_game_counts.c.points_won.label("total_points"),
                                 ).\
                filter( match_game_counts.c.user_id == User.id ).\
                filter( match_game_counts.c.games_won >= 1 ).subquery()
                
    match_losers = session.query(  match_game_counts.c.match_id, 
                                   match_game_counts.c.user_id, 
                                   User.displayname, 
                                   match_game_counts.c.games_lost.label("games_lost"),
                                   match_game_counts.c.points_lost.label("total_points"),
                                ).\
                filter( match_game_counts.c.user_id == User.id ).\
                filter( match_game_counts.c.games_won < 1 ).subquery()
                              
    match_history = session.query(  Match.id.label('id'),
                                    Match.date.label('date'),
                                    match_winners.c.total_points.label('winner_score'), 
                                    match_winners.c.user_id.label('winner_id'),
                                    match_winners.c.displayname.label('winner_displayname'),
                                    match_losers.c.total_points.label('opponent_score'),
                                    match_losers.c.user_id.label('opponent_id'),
                                    match_losers.c.displayname.label('opponent_displayname')).\
                        filter( match_winners.c.match_id == match_losers.c.match_id ).\
                        filter( Match.id == match_winners.c.match_id )
    if filter_user_id:
        if filter_user_id and isinstance(filter_user_id, list):
            match_history = match_history.filter(or_(and_(match_winners.c.user_id==filter_user_id[0], match_losers.c.user_id==filter_user_id[1]),
                                                     and_(match_winners.c.user_id==filter_user_id[1], match_losers.c.user_id==filter_user_id[0])
                                                     ))
        else:
            match_history = match_history.filter(or_(match_winners.c.user_id == filter_user_id, match_losers.c.user_id == filter_user_id))
    
    return match_history

'''
session = SessionFactory()
try:
    print resultdict(get_match_history_query(session).all())
finally:
    session.close()
                    
quit()
'''

sorting_expression = re.compile(r"sort\((?P<direction>[\+|\-])(?P<column>\w+)\)")
range_expression = re.compile(r"items=(?P<lower>\d+)-(?P<upper>\d+)")

class MatchHistoryStore(AutoVerifiedRequestHandler):
    def get(self, match_id):
        username = self.get_current_user()
        
        if username is None:
            self.validate_user()
            return
            
        user = User.get_user(username)
                
        if user.permission_level < constants.PERMISSION_LEVEL_USER:
            self.render("denied.html", user=user)
            return
        
        
        if match_id is not None and match_id != "":
            # single item
            session = SessionFactory()
            try:
                result = get_match_history_query(session).filter(Match.id == match_id).one()
                        
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
                    column = "date"
                    
            if column not in ["id", "date", "winner_id", "winner_score", "winner_displayname", "opponent_id", "opponent_score", "opponent_displayname"]:
                column = "date"

            if direction == '-':
                    direction = desc
            else:
                    direction = asc
            
            session = SessionFactory()
            try:
                query = get_match_history_query(session)
                        
                total = query.count()
            
                query = query.order_by(direction(column))
                        
                query = query.slice(start, stop)
                        
                result = query.all()
                        
                result = resultdict(result)
                
                data = "{}&& "+json.dumps(result)
                self.set_header('Content-range', 'items {}-{}/{}'.format(start, stop, total))
                self.set_header('Content-length', len(data))
                self.set_header('Content-type', 'application/json')
                self.write(data)
                
            finally:
                session.close()

class UserMatchHistoryStore(AutoVerifiedRequestHandler):
    def get(self, target_user_id):
        username = self.get_current_user()
        
        if username is None:
            self.validate_user()
            return
            
        user = User.get_user(username)
                
        if user.permission_level < constants.PERMISSION_LEVEL_USER:
            self.render("denied.html", user=user)
            return
        
        
        if not target_user_id:
            raise ValueError("User required")
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
                column = "date"
                
        if column not in ["id", "date", "winner_id", "winner_score", "winner_displayname", "opponent_id", "opponent_score", "opponent_displayname"]:
            column = "date"

        if direction == '-':
                direction = desc
        else:
                direction = asc
        
        session = SessionFactory()
        try:
            query = get_match_history_query(session, target_user_id)
                    
            total = query.count()
        
            query = query.order_by(direction(column))
                    
            query = query.slice(start, stop)
                    
            result = query.all()
                    
            result = resultdict(result)
            
            data = "{}&& "+json.dumps(result)
            self.set_header('Content-range', 'items {}-{}/{}'.format(start, stop, total))
            self.set_header('Content-length', len(data))
            self.set_header('Content-type', 'application/json')
            self.write(data)
            
        finally:
            session.close()

class HeadToHeadStore(AutoVerifiedRequestHandler):
    def get(self, user1, user2, summary=False):
        username = self.get_current_user()

        if username is None:
            self.validate_user()
            return

        user = User.get_user(username)

        if user.permission_level < constants.PERMISSION_LEVEL_USER:
            self.render("denied.html", user=user)
            return


        if not (user1 and user2):
            raise ValueError("Two users are required")

        user1 = User.by_id(user1)
        user2 = User.by_id(user2)
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
                column = "date"

        if column not in ["id", "date", "winner_id", "winner_score", "winner_displayname", "opponent_id", "opponent_score", "opponent_displayname"]:
            column = "date"

        if direction == '-':
                direction = desc
        else:
                direction = asc

        session = SessionFactory()
        try:
            query = get_match_history_query(session, [user1.id, user2.id])

            total = query.count()

            query = query.order_by(direction(column))
            if not summary:
                query = query.slice(start, stop)

            result = query.all()

            if summary:
                score_dict = {'won': 0, 'lost': 0, 'points_scored': 0, 'difference': 0, 'form': ''}
                sum_dict = { user1.id: score_dict.copy(), user2.id: score_dict.copy() }

                for res in result:
                    sum_dict[res.winner_id]['won'] += 1
                    sum_dict[res.winner_id]['points_scored'] += res.winner_score
                    sum_dict[res.winner_id]['difference'] += res.winner_score-res.opponent_score
                    sum_dict[res.winner_id]['form'] = 'W' + sum_dict[res.winner_id]['form']
                    sum_dict[res.opponent_id]['lost'] += 1
                    sum_dict[res.opponent_id]['points_scored'] += res.opponent_score
                    sum_dict[res.opponent_id]['difference'] += res.opponent_score-res.winner_score
                    sum_dict[res.opponent_id]['form'] = 'L' + sum_dict[res.opponent_id]['form']

                result = []
                for player in sum_dict:
                    user = user1 if player==user1.id else user2
                    player_dict = sum_dict[player]
                    player_dict['form'] = player_dict['form'][-5:]
                    player_dict.update({'id': player, 'displayname': user.displayname})
                    result.append(player_dict)
                start = 0
                stop = 1
                total = 2
            else:
                result = resultdict(result)

            data = "{}&& "+json.dumps(result)
            self.set_header('Content-range', 'items {}-{}/{}'.format(start, stop, total))
            self.set_header('Content-length', len(data))
            self.set_header('Content-type', 'application/json')
            self.write(data)

        finally:
            session.close()
