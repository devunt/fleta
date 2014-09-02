#/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import Column, ForeignKey
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import func


Base = declarative_base()


class Server(Base):
    __tablename__ = 'servers'
    name = Column('server_name', String(16), primary_key=True)
    host = Column('server_host', String(32))
    port = Column('server_port', Integer, default=6667)
    nick = Column('server_nick', String(16), default='플레타')
    password = Column('server_password', String(32), nullable=True, default=None)
    autocmd = Column('server_autocmd', String(64), nullable=True, default=None)
    use_ssl = Column('server_use_ssl', Boolean, default=False)
    autoconnect = Column('server_autoconnect', Boolean, default=True)
    channels = relationship("Channel")


class Channel(Base):
    __tablename__ = 'channels'
    id = Column('channel_id', Integer, primary_key=True)
    server = Column(String, ForeignKey('servers.server_name'))
    name = Column('channel_name', String(32))
    password = Column('channel_password', String(32), nullable=True, default=None)
    use_broadcast = Column('channel_use_broadcast', Boolean, default=False)
    autojoin = Column('channel_autojoin', Boolean, default=True)


class MabiNotice(Base):
    __tablename__ = 'notices'
    id = Column('notice_id', Integer, primary_key=True)
    nid = Column('notice_nid', Integer)
    category = Column('notice_category', String(8))
    title = Column('notice_title', String(64))
    short_title = Column('notice_short_title', String(64))
    author = Column('notice_author', String(16))
    content = Column('notice_content', Text)
    url = Column('notice_url', String(64))
    timestamp = Column('notice_timestamp', DateTime, default=func.now())
