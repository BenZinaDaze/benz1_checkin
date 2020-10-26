import requests
import os

cookie = os.environ["COOKIETS"]
url = "https://www.tsdm39.net/plugin.php?id=np_cliworkdz:work"
data1 = {"act": "clickad"}
data2 = {"act": "getcre"}


def q():
    headers = {
        "user-agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36",
        "cookie": cookie,
        "Referer": "https://www.tsdm39.net/plugin.php?id=np_cliworkdz:work",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": 'application/x-www-form-urlencoded'
    }
    for i in range(6):
        res1 = requests.post(url=url, headers=headers, data=data1).text
        print(res1)
    for i in range(1):
        res2 = requests.post(url=url, headers=headers, data=data2).text
        print(res2)


def main_handler(event, context):
    return q()


if __name__ == "__main__":
    q()