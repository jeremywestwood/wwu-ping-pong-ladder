#!/usr/local/bin/python

import os
import sys
import socket

system_directory = os.path.dirname(os.path.abspath(__file__))

sys.path.append(system_directory + "/imports")

import tornado.web
import tornado.httpserver
import tornado.ioloop

import database
import constants

from handlers import *

handlers = [
    (r'/', FixedUserRequestHandler),
    (r'/(logout|login)$', MainRequestHandler),
    (r'/admin$', AdminHandler),
    (r'/admin/Add-User$', AddUserHandler),
    
    (r"/", tornado.web.RedirectHandler, {"url": "/Leaderboard"}),
    
    (r'/Leaderboard/data/(?:undefined)?(\d*)', LeaderboardStore),
    (r'/Leaderboard/users/(?:undefined)?(\d*)', UserStore),
    
    (r'/Leaderboard/(\d+)/rank/(?:undefined)?(\d*)', RankStore),
    
    (r'/Leaderboard$', UserInfoHandler),
    (r'/Leaderboard/(\d+)$', UserInfoHandler),
    
    (r'/Leaderboard/Match-History/data/(?:undefined)?(\d*)', MatchHistoryStore),
    (r'/Leaderboard/User-Match-History/data/(?:undefined)?(\d*)', UserMatchHistoryStore),
    
    (r'/Leaderboard/Match-History$', GeneralInfoHandler),
    (r'/Leaderboard/Match-History/(\d+)$', GeneralInfoHandler),
    
    (r'/Leaderboard/Record-Match$', RecordMatchHandler),
    (r'/Leaderboard/User-Settings$', UserSettingsHandler),

    (r'/Leaderboard/Head-to-Head$', HeadToHeadHandler),
    (r'/Leaderboard/Head-to-Head/(\d+)/(\d+)$', HeadToHeadHandler),
    (r'/Leaderboard/Head-to-Head/data/(\d+)/(\d+)$', HeadToHeadStore),
    (r'/Leaderboard/Head-to-Head/data/(\d+)/(\d+)/(summary)$', HeadToHeadStore),
]

if __name__ == "__main__":
        tornado_app = tornado.web.Application(  handlers, 
                                                debug=False, 
                                                cookie_secret=constants.COOKIE_SECRET, 
                                                template_path=system_directory+"/templates", 
                                                static_path=system_directory+"/static"
                                             )
        
        tornado_http = tornado.httpserver.HTTPServer(tornado_app)
        tornado_http.bind(8080, family=socket.AF_INET)
        tornado_http.start()
        tornado.ioloop.IOLoop.instance().start()
