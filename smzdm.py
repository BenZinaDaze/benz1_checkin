#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import sys
import requests
import re

SMZDM_COOKIES = os.environ["SMZDM_COOKIES"]

class SMZDMDailyException(Exception):
    def __init__(self, req):
        self.req = req

    def __str__(self):
        return str(self.req)

class SMZDMDaily(object):
    BASE_URL = 'https://zhiyou.smzdm.com'
    CHECKIN_URL = BASE_URL + '/user/checkin/jsonp_checkin'

    def __init__(self):
        self.session = requests.Session()

    def checkin(self):
        headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Host': 'zhiyou.smzdm.com',
            'Referer': 'https://www.smzdm.com/',
            'Sec-Fetch-Dest': 'script',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36',
            }
        self.session.headers = headers
        headers['Cookie'] = SMZDM_COOKIES  
        r = self.session.get(self.CHECKIN_URL)
        if r.status_code != 200:
            raise SMZDMDailyException(r)

        data = r.text
        jdata = json.loads(data)

        return jdata

if __name__ == '__main__':
    try:
        smzdm = SMZDMDaily()
        result = smzdm.checkin()
    except SMZDMDailyException as e:
        print('fail', e)
    except Exception as e:
        print('fail', e)
    else:
        print('success', result)