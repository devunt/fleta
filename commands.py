#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests

from functools import wraps
from time import time

import config


def fleta_cmd(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            r = f(*args, **kwargs)
        except:
            return ('unexpected error (code=-1)',)
        if isinstance(r, str):
            return (r,)
        elif not r:
            return ()
        else:
            return r
    return wrapper


@fleta_cmd
def get_enchant_info(args):
    if args == '':
        return '사용법: ex) %s인챈트 여신의'.format(config.cmd_prefix)
    rows = c.execute("SELECT * FROM enchant WHERE name1 LIKE ? OR name2 LIKE ?", (args, args)).fetchall()
    if len(rows) > 3: rows = rows[:3]
    if not rows:
        rows = [c.execute("SELECT * FROM enchant WHERE name1 LIKE ? OR name2 LIKE ?", ('%%%s%%'%args, '%%%s%%'%args)).fetchone()]
        if not rows[0]:
            return '결과가 없습니다'
    rn = []
    iidx = 0
    for row in rows:
        rt = []
        l = 0
        f = False
        for ro in row['desc'].split('\\n'):
            l += len(ro) + 3
            idx = l / 350
            if len(rt) <= idx: rt.append([])
            if '에 인챈트 가능' in ro:
                rt[idx].append('\00303%s\x0f' % ro)
            elif ro.startswith('['):
                rt[idx].append('\00304%s\x0f' % ro.strip('[]'))
            else:
                if f:
                    rt[idx][-1] += ' \00302%s\x0f' % ro
                else:
                    rt[idx].append('\00302%s\x0f' % ro)
                f = ro.endswith('때')
        for rl in rt:
            rn.append(' / '.join(rl))
        rf = ''
        if row['name1'] == row['name2']: rf = '[%s]' % row['name1']
        else: rf = '[%s, %s]' % (row['name1'], row['name2'])
        rn[iidx] = '\002%s\x0f \x1f(%s랭크, 접%s)\x0f / %s' % (rf, hex(16 - row['rank'])[2].upper(), '미' if row['usage'] else '두', rn[iidx])
        iidx += len(rt)
    return rn


@fleta_cmd
def get_title_info(args):
    if args == '':
        return '사용법: ex) %s타이틀 한 방에 곰을 잡은' % config.cmd_prefix
    rows = c.execute("SELECT * FROM title WHERE mname LIKE ? OR fname LIKE ?", (args, args)).fetchall()
    if len(rows) > 3: rows = rows[:3]
    if not rows:
        rows = [c.execute("SELECT * FROM title WHERE mname LIKE ? OR fname LIKE ?", ('%%%s%%'%args, '%%%s%%'%args)).fetchone()]
        if not rows[0]:
            return '결과가 없습니다'
    rn = []
    iidx = 0
    for row in rows:
        desc = row['desc']
        rt = [['\00303%s\x0f' % desc.replace("\\'", "'")]]
        l = len(desc)
        f = False
        for ro in row['effectdesc'].split('\\n'):
            if ro == '': continue
            l += len(ro) + 3
            idx = l / 350
            if idx != 0 and len(rt) <= idx: rt.append([])
            if ro.startswith('['):
                rt[idx].append('\00304%s\x0f' % ro.strip('[]'))
            else:
                rt[idx].append('\00302%s\x0f' % ro)
        for rl in rt:
            rn.append(' / '.join(rl))
        rf = ''
        if row['mname'] == row['fname']: rf = '[%s]' % row['mname']
        else: rf = '[%s, %s]' % (row['mname'], row['fname'])
        ry = ['일반 (숫자)', '아르바이트용', '일반', '특수', '펫/몹용', '잘난체 스테이크', '2차 타이틀']
        rn[iidx] = '\002%s\x0f \x1f(%s)\x0f / %s' % (rf, ry[row['type']-1], rn[iidx])
        iidx += len(rt)
    return rn


@fleta_cmd
def get_shadow_mission(args):
    try:
        res = requests.get('https://mabi-api.sigkill.kr/get_todayshadowmission/today?mode=withinfo').json()
    except:
        return 'unexpected error (code=0)'
    r = []
    a = ''
    l = '하드'
    m = {'초급': [1, 1], '중급': [1.8, 1.4], '고급': [3, 2], '하드': [5, 3], '엘리트': [7, 4]}
    tt = res['Taillteann']['normal']
    tr = res['Tara']['normal']
    if args.split(' ')[0] == '피시방':
        tt = res['Taillteann']['pcbang']
        tr = res['Tara']['pcbang']
        args = args[10:]
        a = '피시방, '
    if args != '' and not m.get(args):
        return '사용법: ex) !그림자 중급 / !그림자 피시방 엘리트'
    args = '하드' if args == '' else args
    r.append('[탈틴] \002%s\x0f \x1f(%s%d~%d인)\x0f ※ %s 기준 [경험치 %d / %d 골드]' % (tt['name'], a, tt['minMembers'], tt['maxMembers'], args, tt['exp']*m[args][0], tt['gold']*m[args][1]))
    r.append('[타라] \002%s\x0f \x1f(%s%d~%d인)\x0f ※ %s 기준 [경험치 %d / %d 골드]' % (tr['name'], a, tr['minMembers'], tr['maxMembers'], args, tr['exp']*m[args][0], tr['gold']*m[args][1]))
    return r


@fleta_cmd
def get_erinn_time(args):
    now = time()
    h = int((now / 90) % 24)
    m = int((now / 1.5) % 60)
    p = '전'
    if h >= 12:
        p = '후'
        if h >= 13:
            h -= 12
    return '현재 에린 시간: 오%s %d시 %d분' % (p, h, m)


@fleta_cmd
def toggle_realtime_broadcast(args):
    pass # implemented in fleta.py


@fleta_cmd
def show_help(args):
    l = []
    for cmd in cmdfuncs:
        l.append(config.cmd_prefix + cmd)
    return '명령어 목록: ' + ' / '.join(l)


cmdfuncs = {
    '인챈트': get_enchant_info,
    '타이틀': get_title_info,
    '그림자': get_shadow_mission,
    '마비시간': get_erinn_time,
    '에린시간': get_erinn_time,
    '실시간': toggle_realtime_broadcast,
    '도움말': show_help,
}


def handle(line):
    cmd, t, args = line[1:].partition(' ')
    f = cmdfuncs.get(cmd)
    if f:
        args = args.strip()
        return f(args)
    else:
        return tuple()
