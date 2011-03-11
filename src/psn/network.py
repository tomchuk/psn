#!/usr/bin/env python

from BeautifulSoup import BeautifulSoup
import cookielib
import json
import os
from random import random
import urllib
import urllib2
import urlparse


## File to store cookies
COOKIE_JAR = 'cookies.lwp'


## Default set of headers for requests to PSN
DEFAULT_HEADERS = {
    'User-agent':       'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1)',
    'Accept':           '*/*',
    'Accept-Encoding':  'gzip, deflate',
    'Accept-Language':  'en-US',
    'Connection':       'Keep-Alive',
}

## These cookies must be set to skip logon
REQUIRED_COOKIES = ['PSNS2STICKET', 'Register', 'SCEAuserinfo', 'TICKET', 'betaCookie', 'op.an', 'ps-qa.si', 'psnInfoCk', 'userinfo']


cookie_jar = cookielib.LWPCookieJar()
if os.path.isfile(COOKIE_JAR):
    cookie_jar.load(COOKIE_JAR)
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie_jar))
urllib2.install_opener(opener)


class Friend(object):

    def __init__(self, handle):
        self.handle = handle
        self._online = None
        self._avatar = None
        self._playing = None

    @property
    def online(self):
        if self._online is None:
            self._update()
        return self._online

    @property
    def avatar(self):
        if self._avatar is None:
            self._update()
        return self._avatar

    @property
    def playing(self):
        if self._playing is None:
            self._update()
        return self._playing


    def _update(self):
        url = 'http://us.playstation.com/playstation/psn/profile/%s?id=%f' % (self.handle, random())
        headers = DEFAULT_HEADERS
        headers.update({
            'Referer': 'http://us.playstation.com/playstation/psn/profile/friends?id=%f' % random(),
            'X-Requested-With': 'XMLHttpRequest',
        })
        rq = urllib2.Request(url=url, headers=headers)
        rs = unicode(urllib2.urlopen(rq, timeout=10000).read(), errors='ignore')
        soup = BeautifulSoup(rs)

        try:
            self._avatar = soup.find('div', {'class': 'avatar'}).find('img')['src'].split('=', 1)[1]
        except:
            self._avatar = u''

        try:
            self._online = bool(soup.find('div', {'class': 'oStatus'}).find('div', {'class': 'onlineStatus online'}))
        except:
            self._online = False

        try:
            self._playing = soup.find('span', {'class': '_iamplaying_'}).text
        except:
            self._playing = u''



class PSN(object):

    def __init__(self, email, passwd):
        self._handle = None
        self._email = email
        self._passwd = passwd
        self._friends = None

    @property
    def handle(self):
        if not self._handle:
            self._login()
        return self._handle

    def _login(self):

        ## Check for valid stored cookes. If valid, set handle and return
        if [i.name for i in cookie_jar] == REQUIRED_COOKIES:
            self._handle = urlparse.parse_qs([i.value for i in cookie_jar if i.name=='SCEAuserinfo'][0])['psHandle'][0]
            return


        ## Post the login form to get a session id
        url = 'https://store.playstation.com/j_acegi_external_security_check?target=/external/login.action'
        data = {'j_username': self._email,
                'j_password': self._passwd,
                'returnURL': 'http://www.psnapi.com.ar/ps3/login.aspx'}
        headers = DEFAULT_HEADERS
        headers.update({'Referer': 'https://store.playstation.com/external/index.vm?returnURL=http://www.psnapi.com.ar/ps3/login.aspx'})
        rq = urllib2.Request(url=url, data=urllib.urlencode(data), headers=headers)

        # Store session id
        sess_id = urllib2.urlopen(rq, timeout=10000).read()

        ## Hammer at a few urls for the proper cookies
        del headers['Referer']
        url = 'http://us.playstation.com/uwps/PSNTicketRetrievalGenericServlet?sessionId=%s' % (sess_id)
        rq = urllib2.Request(url=url, headers=headers)
        try:
            urllib2.urlopen(rq, timeout=10000)
        except urllib2.HTTPError:
            pass # this just happens, but it needs to happen

        url = 'http://us.playstation.com/uwps/HandleIFrameRequests?sessionId=%s' % (sess_id)
        rq = urllib2.Request(url=url, headers=headers)
        urllib2.urlopen(rq, timeout=10000)

        url = 'http://us.playstation.com/uwps/CookieHandler'
        headers.update({'Referer': 'http://us.playstation.com/portableid/index.htm'})
        rq = urllib2.Request(url=url, headers=headers)
        rs = urllib2.urlopen(rq, timeout=10000).read()

        # Store handle
        self._handle = rs.split(',')[0].replace('handle=','')
        cookie_jar.save(COOKIE_JAR)

    @property
    def friends(self):
        if self._friends is not None:
            return self._friends

        if self._handle is None:
            self._login()

        self._friends = []

        url = 'http://us.playstation.com/playstation/psn/profile/get_friends_names'
        headers = DEFAULT_HEADERS
        headers.update({'Referer': 'http://us.playstation.com/myfriends/'})
        rq = urllib2.Request(url=url, headers=headers)
        rs = urllib2.urlopen(rq, timeout=10000).read()
        friend_handles = sorted(json.loads(rs), key=unicode.lower)

        for handle in friend_handles:
            self._friends.append(Friend(handle))
        return self._friends
