#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import re
import requests

from html.parser import HTMLParser
import lxml.html


RE_NOTICE_CONTENT = re.compile(r'<td class="view_notice_area" id="view_area">(.+)</td>')
RE_PATCH_ACCEPT = re.compile(r'patch_accept=(0|1)')
RE_MAIN_VERSION = re.compile(r'main_version=(.+)')


def get_mabinogi_notices():
    res = requests.get('http://mabinogi.nexon.com/C3/News/Notice.asp').text
    page = lxml.html.fromstring(res)
    notice_nodes = page.xpath('//*[@id="subContents"]/div[3]/table/tr[@class="strong_0"]')
    notices = dict()
    for notice in notice_nodes:
        title = notice.xpath('td[2]/a/text()')[0]
        nid = int(notice.xpath('td[2]/a/@href')[0][28:])
        notices[nid] = title
    return notices


def get_mabinogi_notice(nid):
    url = 'http://mabinogi.nexon.com/C3/News/Notice.asp?mode=view&ReadSn={0}'.format(nid)
    res = requests.get(url).text
    page = lxml.html.fromstring(res)
    category = page.xpath('//*[@id="subContents"]/div[3]/div[1]/div[1]/img/@alt')[0]
    title = page.xpath('//*[@id="subContents"]/div[3]/div[1]/div[1]/span/text()')[0]
    author = page.xpath('//*[@id="subContents"]/div[3]/div[2]/div/font/text()')[0]
    content = page.xpath('//*[@id="view_area"]')[0]
    content = HTMLParser().unescape(lxml.html.tostring(content).decode())

    ret = {
        'category': category,
        'title': title,
        'author': author,
        'content': content,
        'url': url,
    }
    ret = {k: v.strip() for k, v in ret.items()}
    ret['nid'] = nid
    return ret


def get_patch_txt():
    res = requests.get('http://211.218.233.238/patch/patch.txt').text
    #res = requests.get('http://211.218.233.238/patch/patch_test.txt').text
    m = RE_PATCH_ACCEPT.search(res)
    patch_accept = m.group(1)
    m = RE_MAIN_VERSION.search(res)
    main_version = m.group(1)

    return {
        'patch_accept': patch_accept,
        'main_version': main_version,
    }
