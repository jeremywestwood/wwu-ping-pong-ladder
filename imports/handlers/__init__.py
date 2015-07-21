
#page handlers
from MainRequestHandler import MainRequestHandler
from GeneralInfoHandler import GeneralInfoHandler
from UserInfoHandler import UserInfoHandler
from RecordMatchHandler import RecordMatchHandler
from UserSettingsHandler import UserSettingsHandler

from FakeUserRequestHandler import FakeUserRequestHandler
from FixedUserRequestHandler import FixedUserRequestHandler, AutoVerifiedRequestHandler

#data handlers
from LeaderboardStore import LeaderboardStore
from MatchHistoryStore import MatchHistoryStore
from UserStore import UserStore
from RankStore import RankStore