"""
什么值得买自动签到脚本
使用github actions 定时执行
@author : stark
"""
import requests,os
import time

"""
请求头
"""
DEFAULT_HEADERS = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive',
        'Host': 'zhiyou.smzdm.com',
        'Referer': 'http://www.smzdm.com/qiandao/',
        'Sec-Fetch-Dest': 'script',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36',
        }

class SMZDM_Bot(object):
    def __init__(self):
        self.session = requests.Session()
        # 添加 headers
        self.session.headers = DEFAULT_HEADERS

    def __json_check(self, msg):
        """
        对请求 盖乐世社区 返回的数据进行进行检查
        1.判断是否 json 形式
        """
        try:
            result = msg.json()
            print(result)
            return True
        except Exception as e:
            print(f'Error : {e}')            
            return False

    def load_cookie_str(self, cookies):
        """
        起一个什么值得买的，带cookie的session
        cookie 为浏览器复制来的字符串
        :param cookie: 登录过的社区网站 cookie
        """
        self.session.headers['Cookie'] = cookies    

    def checkin(self):
        """
        签到函数
        """
        url = 'https://zhiyou.smzdm.com/user/checkin/jsonp_checkin'
        msg = self.session.get(url)
        if self.__json_check(msg):
            return msg.json()
        return msg.content

    def push_to_wechat(text,desp,secretKey):
        """
        通过serverchan将消息推送到微信
        :param secretKey: severchan secretKey
        :param text: 标题
        :param desp: 内容
        :return resp: json
        """
        url = f'http://sc.ftqq.com/{secretKey}.send'
        session = requests.Session()
        data = {'text':text,'desp':desp}
        resp = session.post(url,data = data)
        return resp.json()



if __name__ == '__main__':
    sb = SMZDM_Bot()
    cookies = os.environ["COOKIES"]
    SERVERCHAN_SECRETKEY = os.environ["SERVERCHAN_SECRETKEY"]
    sb.load_cookie_str(cookies)
    res = sb.checkin()
    print(res)
    resp = sb.push_to_wechat('什么值得买每日签到',
                    str(res),
                    SERVERCHAN_SECRETKEY)
    print(resp)