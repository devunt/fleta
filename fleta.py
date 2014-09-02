#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio

from collections import defaultdict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm import load_only

import config
import commands
import polls

from db import Base, Channel, MabiNotice, Server


loop = asyncio.get_event_loop()

engine = create_engine(config.database_url)
session = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine))

if __name__ != '__main__':
    Base.metadata.create_all(bind=engine)
    import bot


class MabiPoller(object):
    running = False
    notice_category_colors = {
        '공지': '04',
        '점검': '07',
        '샵': '12',
        '행사': '12',
    }

    def start(self, raise_exc=True):
        if not self.running:
            self.running = True
        elif raise_exc:
            raise Exception('Already started')

    def stop(self, raise_exc=True):
        if self.running:
            self.running = False
        elif raise_exc:
            raise Exception('Already stopped')

    def poll(self):
        if not self.running:
            return
        cur_notices = polls.get_mabinogi_notices()
        last_notice = sorted(cur_notices.keys())[0]
        notice_rows = session.query(MabiNotice).options(load_only('nid', 'short_title')).filter(MabiNotice.nid >= last_notice).order_by(MabiNotice.id.desc()).limit(10).all()
        notices = {notice.nid: notice.short_title for notice in notice_rows}

        for nid, title in cur_notices.items():
            continue
            if not any(x in title for x in ('수정', '추가')):
                continue
            notice = polls.get_mabinogi_notice(nid)
            #session.query(MabiNotice).
            #notice['content']

        new_notices = sorted(set(cur_notices.items()) - set(notices.items()))
        for nid, title in new_notices:
            notice = polls.get_mabinogi_notice(nid)
            notice_row = MabiNotice(short_title=title, **notice)
            session.add(notice_row)
            session.commit()
            msg = '## \003{0}({category})\x0f \002[{title}]\x0f {url}'.format(self.notice_category_colors[notice['category']], **notice)
            broadcast(msg)

        patch_accept, main_version = polls.get_patch_txt()


class FletaIRCHandler(bot.IRCHandler):
    def on_welcome(self):
        poller.start(False)
        autocmd = session.query(Server).filter(Server.name == self._server_name).first().autocmd
        self.send_raw_line(autocmd)
        channels = get_channels_query(self._server_name).filter(Channel.autojoin == True)
        for channel in channels:
            self.send_raw_line('JOIN {0} {1}', channel.name, channel.password)

    def on_invite(self, nick, channel):
        self.send_raw_line('JOIN {0}', channel)

    def on_join(self, nick, channel):
        if self._nick != nick:
            return
        chan_row = get_channels_query(self._server_name).filter(Channel.name == channel).first()
        if chan_row:
            chan_row.autojoin = True
            session.commit()
        else:
            chan_row = Channel(server=self._server_name, name=channel)
            session.add(chan_row)
            session.commit()
            self.say(channel, '마비노기 종합 정보 봇 {0}입니다. 사용 가능한 명령은 {1}도움말 을 통해서 볼 수 있습니다.', self._nick, config.cmd_prefix)
            self.say(channel, '실시간으로 채널 메시지를 통해 마비노기 서버 상황과 공지 등을 받아보고 싶으시다면 {0}실시간 으로 설정 하실 수 있습니다. (토글 방식, 기본값: 해제)', config.cmd_prefix)

    def on_kick(self, nick, by_nick, channel, reason):
        if self._nick != nick:
            return
        chan_row = get_channels_query(self._server_name).filter(Channel.name == channel).first()
        if chan_row:
            chan_row.autojoin = False
            session.commit()

    def on_privmsg(self, nick, host, channel, message):
        if not channel.startswith('#'):
            return
        if message.startswith('-') and host == config.irc_admin_host:
            message = message[1:]
            if message == 'startpolling':
                poller.start()
                self.say(channel, 'polling started.')
            elif message == 'stoppolling':
                poller.stop()
                self.say(channel, 'polling stopped.')
            elif message == 'broadcast':
                broadcast('test broadcast')
        elif message.startswith('{0}실시간'.format(config.cmd_prefix)):
            f = get_channels_query(self._server_name).filter(Channel.name == channel).first()
            v = not f.use_broadcast
            f.use_broadcast = v
            session.commit()
            self.say(channel, '실시간 알림을 {0}했습니다', '설정' if v else '해제')
        elif message.startswith(config.cmd_prefix):
            lines = commands.handle(message)
            for line in lines:
                self.say(channel, line)


handlers = dict()
poller = MabiPoller()

def add_handler(server_name, nick, writer):
    handlers[server_name] = FletaIRCHandler(server_name, nick, writer)

def irc_handle(server_name, line):
    handlers[server_name].on_line(line)

def get_channels_query(server_name):
    return session.query(Channel).join(Server).filter(Server.name == server_name)

def send_raw_line(server_name, line, *args, **kwargs):
    handlers[server_name].send_raw_line(line, *args, **kwargs)

def broadcast(line):
    channels = defaultdict(lambda: channels)
    for channel in session.query(Channel):
        channels[channel.server][channel.name] = channel.use_broadcast
    for name, handler in handlers.items():
        for channel in handler.channels:
            if channels[name][channel]:
                handler.say(channel, line)
