# -*- coding: utf8 -*-
import requests, json, time, os

requests.packages.urllib3.disable_warnings()

cookie = os.environ.get("SMZDM_COOKIES")

def smzdm_pc(*arg):
    SCKEY = os.environ.get('SECRETKEY')
    s = requests.Session()
    s.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36'})
    t = round(int(time.time() * 1000))
    url = f'https://zhiyou.smzdm.com/user/checkin/jsonp_checkin?_={t}'

    headers = {
        "cookie" : cookie,
        'Referer': 'https://www.smzdm.com/'
        }

    r = s.get(url, headers=headers, verify=False)
    print(r.text)
    if r.json()["error_code"] != 0 and SCKEY:
        scurl = f"https://sc.ftqq.com/{SCKEY}.send"
        data = {
                "text" : "smzdm  Cookie过期",
                "desp" : r.text
                }
        requests.post(scurl, data=data)
        print("smzdm cookie失效")

if __name__ == "__main__":
    if cookie:
        smzdm_pc()

    