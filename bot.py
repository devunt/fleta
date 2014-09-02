#/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import re
import ssl
import subprocess
import sys
import traceback

from importlib import reload
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

import config

from db import Server


RE_IRCLINE = re.compile("^(:(?P<prefix>[^ ]+) +)?(?P<command>[^ ]+)(?P<params>( +[^:][^ ]*)*)(?: +:(?P<message>.*))?$")

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] {%(levelname)s} %(message)s')
#logging.getLogger('asyncio').setLevel(logging.CRITICAL)
logging.getLogger().setLevel(config.loglevel)

loop = asyncio.get_event_loop()

engine = create_engine(config.database_url)
session = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine))


class IRCHandler(object):
    channels = list()

    def __init__(self, server_name, nick, writer):
        self._server_name = server_name
        self._nick = nick
        self._writer = writer

    def on_welcome(self): pass
    def on_invite(self, nick, channel): pass
    def on_join(self, nick, channel): pass
    def on_kick(self, nick, by_nick, channel, reason): pass
    def on_part(self, nick, channel, reason): pass
    def on_quit(self, nick, channel, reason): pass
    def on_privmsg(self, nick, host, channel, message): pass

    def on_ping(self, message):
        self.send_raw_line('PONG :{0}', message)

    def on_line(self, line):
        _nick = lambda x: x.split('!')[0]
        _host = lambda x: x.split('@')[1]
        m = RE_IRCLINE.match(line)
        if m:
            prefix = m.group('prefix')
            command = m.group('command').lower()
            params = (m.group('params') or '').split() or ['']
            message = m.group('message') or ''
            if command == 'ping':
                self.on_ping(message)
            elif command == '001':
                self.on_welcome()
            elif command == 'invite':
                self.on_invite(_nick(prefix), message)
            elif command == 'join':
                if _nick(prefix) == self._nick:
                    self.channels.append(message.lower())
                self.on_join(_nick(prefix), message.lower())
            elif command == 'kick':
                if _nick(params[1]) == self._nick:
                    self.channels.remove(params[0].lower())
                self.on_kick(params[1], _nick(prefix), params[0].lower(), message)
            elif command == 'part':
                if _nick(prefix) == self._nick:
                    self.channels.remove(message.lower())
                self.on_part(_nick(prefix), params[0].lower(), message)
            elif command == 'quit':
                if _nick(prefix) == self._nick:
                    self.channels = list()
                self.on_quit(_nick(prefix), params[0].lower(), message)
            elif command == 'privmsg' and message == '-rehash' and _host(prefix) == config.irc_admin_host:
                handlers = fleta.handlers
                fleta.poller.stop(False)
                reload(config)
                reload(fleta)
                reload(commands)
                reload(polls)
                fleta.poller.start(False)
                for handler in handlers.values():
                    fleta.add_handler(handler._server_name, handler._nick, handler._writer)
                self.send_raw_line('PRIVMSG {0} : rehashed.', params[0])
            elif command == 'privmsg':
                self.on_privmsg(_nick(prefix), _host(prefix), params[0].lower(), message)

    def send_raw_line(self, line, *args, **kwargs):
        self._writer.write(('{0}\n'.format(line.format(*args, **kwargs))).encode('utf-8'))
        logging.debug('[IRC] >>> {0}'.format(line.format(*args, **kwargs)))

    def say(self, channel, line, *args, **kwargs):
        self.send_raw_line('PRIVMSG {0} : {1}'.format(channel, line.format(*args, **kwargs)))


@asyncio.coroutine
def start_mabi_polling():
    def _poll():
        try:
            fleta.poller.poll()
        except:
            ty, exc, tb = sys.exc_info()
            traceback.print_exception(ty, exc, tb)
        finally:
            loop.call_later(10, _poll)
    _poll()


@asyncio.coroutine
def start_irc_loop(name, host, port=6667, nick='플레타', use_ssl=False, password=False):
    while True:
        irc_reader, irc_writer = yield from asyncio.open_connection(host=host, port=port, ssl=use_ssl)
        fleta.add_handler(name, nick, irc_writer)
        fleta.send_raw_line(name, 'USER {0} 8 * :{0}', nick)
        fleta.send_raw_line(name, 'NICK {0}', nick)
        if password:
            fleta.send_raw_line(name, 'PASS {0}', password)
        while True:
            try:
                line = yield from irc_reader.readline()
                line = line.rstrip().decode('utf-8', 'ignore')
            except EOFError:
                break
            if not line:
                break
            logging.debug('[IRC] <<< {0}'.format(line))
            try:
                fleta.irc_handle(name, line)
            except Exception:
                ty, exc, tb = sys.exc_info()
                fleta.send_raw_line(name, 'PRIVMSG %s :ERROR! %s %s' % (config.irc_admin_channel, ty, exc))
                traceback.print_exception(ty, exc, tb)
        yield from asyncio.sleep(10)


@asyncio.coroutine
def start_irc_bots():
    servers = session.query(Server).filter(Server.autoconnect == True)
    for server in servers:
        asyncio.async(start_irc_loop(server.name, server.host, server.port, server.nick, server.use_ssl, server.password))


def main():
    try:
        asyncio.async(start_irc_bots())
        asyncio.async(start_mabi_polling())
        loop.run_forever()
    except KeyboardInterrupt:
        print('bye')
    finally:
        loop.close()


if __name__ == '__main__':
    sys.modules['bot'] = sys.modules['__main__']
    import fleta, commands, polls
    main()
