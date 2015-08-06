from sqlalchemy import Sequence
from sqlalchemy import Column, Integer

from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref

from Base import Base

class FloatingTrophyCache(Base):
    __tablename__ = 'floating_trophy'

    id = Column(Integer, Sequence('floating_trophy_id_seq'), primary_key=True)
    
    match_id = Column(Integer, ForeignKey('matches.id'))
    match = relationship("Match", backref=backref('floating_trophy', order_by=id))
    
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User", backref=backref('floating_trophies', order_by=id))

    def __init__(self):
        pass