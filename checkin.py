# -*- coding: UTF-8 -*-
import argparse
import json
import logging
import os
import re
import sys
import threading
import time
import warnings
from urllib.parse import urlparse

import cfscrape
import requests
from lxml import etree

import boto3
import botocore
from boto3.dynamodb.conditions import Key

from pprint import pprint

warnings.filterwarnings('ignore')

parser = argparse.ArgumentParser()

'''
run explame

checkin.py tsdm.cookies.json -t tsdm -f 0a0000a0 -hook http://127.0.0.1

checkin.py tsdm.cookies.json -t tsdm -f 0a0000a0
checkin.py zod.cookies.json -t zod -f 0a0000a0 -p socks5h://127.0.0.1:1080
checkin.py zod.cookies.json -t zod -f 0a0000a0 -l 20 -i 5 -p socks5h://127.0.0.1:1080
# ↑ 5ms run once, total 20s.

'''

parser.add_argument('cookies', nargs=1, help='input cookies json file')
parser.add_argument('-f', '-formhash', '--formhash', help='formhash value', metavar="formhash")
parser.add_argument('-p', '-proxy', '--proxy', help='use proxy', metavar="proxy url")
parser.add_argument('-l', '-loop', '--loop', type=int, help='loop time secound, default 10ms run once',
                    metavar="LOOP_TIME")
parser.add_argument('-i', '-interval', '--interval', type=int, default=10, help='loop interval, ms, default 10',
                    metavar="LOOP_INTERVAL")
parser.add_argument('-t', '-type', '--type', choices=['tsdm', 'zod'], help='choices checkin site, tsdm、zod',
                    metavar="CHECKIN_SITE", required=False)
parser.add_argument('-hook', '--hook', help='call web hook url, post json data {"msg": "msg content"} in body',
                    metavar="call web hook url")
parser.add_argument("-cf", "--cf", help="pass Cloudflare's anti-bot page", action="store_true")
args = parser.parse_args()

formhash = args.formhash
proxy = args.proxy
site_type = args.type
loopTime = args.loop
interval = args.interval
IS_CF = args.cf
COOKIES_FILE = os.path.realpath(os.path.join(os.getcwd(), args.cookies[0]))

HOOK_URL = args.hook

PROGRAM_DIR_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))
# CACHE_FILE_PATH = os.path.join(PROGRAM_DIR_PATH, 'CACHE.json')

DYNAMODB_TABLE_NAME = 'CheckinCache'

taskTimer = None

logging.basicConfig(level=logging.INFO, format='{} - %(asctime)s \n\t %(levelname)s - %(message)s'.format(COOKIES_FILE))
logger = logging.getLogger(__name__)

URL_LINK = {
    "tsdm": {
        "formhash": "https://www.tsdm39.net/forum.php",
        "checkin": "https://www.tsdm39.net/plugin.php?id=dsu_paulsign:sign&operation=qiandao&infloat=1&sign_as=1"
                   "&inajax=1",
        "checkin-status": {
            "sign": "https://www.tsdm39.net/plugin.php?id=dsu_paulsign:sign",
            "checkinInfoXpath": '//*[@class="mn"]/p',
            "hasCheckinXpath": 'string(//*[@class="mt"][1])'
        },
        "template": {
            "formhash": "",
            "qdxq": "wl",
            "todaysay": "HHHHH",
            "qdmode": "3",
            "fastreply": "0"
        }
    }
}

HEADERS = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/70.0.3538.77 Safari/537.36 '
}

COOKIES = {}

PROXIES = None
if proxy is not None:
    PROXIES = {
        'http': proxy,
        'https': proxy
    }


def checkin(url, data):
    r = requests.post(url, data=data, headers=HEADERS, cookies=COOKIES, proxies=PROXIES, verify=False, timeout=60)
    content = r.text
    if content.find('登录') != -1:
        logger.info('cookies expire')
        sys.exit(0)
    if content.find('未定义操作') != -1:
        return {'error': 'formhash'}
    result = re.search('(.*?)</div>', content).group(1)
    return result


def get_formhash(url):
    r = requests.get(url, headers=HEADERS, cookies=COOKIES, proxies=PROXIES, verify=False, timeout=60)
    html_etree = etree.HTML(r.text)
    formhash = html_etree.xpath("//*[@name='formhash']/@value")
    formhash = ''.join(formhash)
    if len(formhash) == 0:
        formhash = re.match('.*;formhash=(\w*).*', r.text, re.S).group(1)
    return formhash


def read_cookies_file():
    try:
        temp, ext = os.path.splitext(COOKIES_FILE)
        if ext.lower() == '.json':
            with open(COOKIES_FILE, mode='r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    cookies = {obj['name']: obj['value'] for obj in data}
                else:
                    cookies = data
        else:
            cookies = {}
            f = open(COOKIES_FILE, 'r')
            for line in f.readlines():
                line = line.strip()
                key = line[0:line.index('=')]
                val = line[line.index('=') + len('='):]
                if val.rfind(';') == len(val) - 1:
                    val = val[0: len(val) - 1]
                cookies[key] = val
    finally:
        if f:
            f.close()
    return cookies


def do_checkin(url, data):
    result = checkin(url, data)
    if isinstance(result, dict) and 'error' in result.keys():
        if result['error'] == 'formhash':
            logger.info("formhash: {}  错误，重新获取 formhash".format(data['formhash']))
            data['formhash'] = get_formhash(URL_LINK[site_type]['formhash'])
            logger.info("当前 formhash: {}".format(data['formhash']))
            result = checkin(url, data)
    logger.info("{}".format(result))


def loop_do_checkin(file, url, data, start_time, loop_time):
    now_time = time.time()
    if now_time - start_time < loop_time:
        global taskTimer
        taskTimer = threading.Timer(interval / 1000, loop_do_checkin, (file, url, data, start_time, loop_time,))
        taskTimer.start()
    do_checkin(url, data)


def get_checkin_info(check_status_obj):
    url = check_status_obj['sign']
    has_checkin_xpath = check_status_obj['hasCheckinXpath']
    checkin_info_xpath = check_status_obj['checkinInfoXpath']
    r = requests.get(url, headers=HEADERS, cookies=COOKIES, proxies=PROXIES, verify=False, timeout=60)
    html_etree = etree.HTML(r.text)
    has_checkin = html_etree.xpath(has_checkin_xpath)
    logger.info(has_checkin)
    if has_checkin.find('已经签到') == -1:
        return

    # toDay = time.strftime("%Y%m%d")
    # if toDay == CACHE[site_type]:
    # 	return

    checkin_info_count = html_etree.xpath('count(' + checkin_info_xpath + ')')
    checkin_info_list = []
    for i in range(int(checkin_info_count)):
        p = html_etree.xpath('string(' + checkin_info_xpath + '[' + str(i) + '])')
        if p is not None:
            checkin_info_list.append(p)
    checkin_info = '\n'.join(checkin_info_list)
    # logger.info('{}'.format(checkin_info))
    # if command is not None:
    # 	command_line = Template(command).substitute(info=checkinInfo)
    # 	print(command_line)
    # 	command_args = shlex.split(command_line)
    # 	try:
    # 		subprocess.check_call(command_args)
    # 	except subprocess.CalledProcessError:
    # 		traceback.print_exc()
    # CACHE[site_type] = toDay
    checkin_date = re.findall('(\\d{4}-\\d{2}-\\d{2})', checkin_info)
    if len(checkin_date) > 0  and False:
        checkin_date = checkin_date[0]
        create_cache_table()
        cache_date = get_cache()
        if cache_date is None:
            put_cache(checkin_date)
        elif cache_date == checkin_date:
            return
        else:
            update_cache(checkin_date)

        # data = {}
        # if os.path.exists(CACHE_FILE_PATH):
        #     with open(CACHE_FILE_PATH, mode='r', encoding='utf-8') as f:
        #         try:
        #             data = json.load(f)
        #         except Exception:
        #             pass
        #         finally:
        #             f.close()
        # if COOKIES_FILE in data.keys() and data[COOKIES_FILE] == checkin_date:
        #     return
        #
        if HOOK_URL is not None:
            payload = {'msg': checkin_info}
            logger.info('Send msg: {} to {}'.format(payload, HOOK_URL))
            requests.post(HOOK_URL, json=payload)

        #
        # data[COOKIES_FILE] = checkin_date
        # with open(CACHE_FILE_PATH, mode='w', encoding='utf-8') as f:
        #     json.dump(data, f)
        #     f.close()


def use_cf(site_obj):
    url_info = urlparse(site_obj['checkin'])
    domain_url = url_info.scheme + '://' + url_info.netloc
    cookie_value, user_agent = cfscrape.get_tokens(domain_url, proxies=PROXIES)
    HEADERS['user-agent'] = user_agent
    COOKIES.update(cookie_value)


def main():
    logger.info("Start")
    global COOKIES
    COOKIES = read_cookies_file()

    site_obj = URL_LINK[args.type]

    if IS_CF:
        use_cf(site_obj)

    global formhash
    if formhash is None:
        formhash = get_formhash(site_obj['formhash'])
    # logger.info('Use formhash: {}'.format(formhash))
    data = site_obj['template']
    data['formhash'] = formhash

    if loopTime is None:
        do_checkin(site_obj['checkin'], data)
    else:
        start_time = time.time()
        loop_do_checkin(COOKIES_FILE, site_obj['checkin'], data, start_time, loopTime)
    global taskTimer
    while taskTimer is not None and not taskTimer.is_alive():
        time.sleep(5)
    if HOOK_URL is not None:
        get_checkin_info(site_obj['checkin-status'])


def get_dynamodb():
    return boto3.resource('dynamodb', region_name='ap-southeast-1')


def create_cache_table(dynamodb=None):
    if not dynamodb:
        dynamodb = get_dynamodb()
    try:
        table = dynamodb.create_table(
            TableName=DYNAMODB_TABLE_NAME,
            KeySchema=[
                {
                    'AttributeName': 'type',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'type',
                    'AttributeType': 'S'
                }

            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }
        )
        return table
    except Exception as e:
        pass


def put_cache(date, dynamodb=None):
    if not dynamodb:
        dynamodb = get_dynamodb()
    table = dynamodb.Table(DYNAMODB_TABLE_NAME)

    response = table.put_item(
        Item={
            'type': site_type,
            'date': date
        }
    )
    return response


def query_cache(dynamodb=None):
    if not dynamodb:
        dynamodb = get_dynamodb()

    table = dynamodb.Table(DYNAMODB_TABLE_NAME)
    response = table.query(
        KeyConditionExpression=Key('type').eq(site_type)
    )
    return response['Items']


def get_cache():
    cache = query_cache()
    if len(cache) > 0:
        pprint(cache)
        return cache[0]['date']
    return None


def set_cache(date):
    put_cache(date)


def update_cache(date, dynamodb=None):
    if not dynamodb:
        dynamodb = get_dynamodb()

    table = dynamodb.Table(DYNAMODB_TABLE_NAME)
    response = table.update_item(
        Key={
            'type': site_type
        },
        UpdateExpression="set #d=:date",
        ExpressionAttributeValues={
            ':date': date,
        },
        ExpressionAttributeNames={
            "#d": 'date'
        },
        ReturnValues="UPDATED_NEW"
    )
    return response


def delete_cache_table(dynamodb=None):
    if not dynamodb:
        dynamodb = get_dynamodb()

    table = dynamodb.Table(DYNAMODB_TABLE_NAME)
    table.delete()


if __name__ == '__main__':
    main()