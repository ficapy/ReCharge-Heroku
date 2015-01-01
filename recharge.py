__author__ = 'LD'
#coding:utf-8

import requests
from hashlib import md5
import time
import random
import sys
import unittest

###huafeiduo API
API_KEY = "--------------------------"
SECRET_KEY = "----------------------------"
telephone_number = "--------------------"

###nexmo API
KEY = "---------------"
SECERT = "--------------------"
my_phone_number = "----------------"


class recharge(object):
    def __init__(self, money=(1, 2, 5, 10, 20, 50, 100, 300)):
        self.money = money
        pass

    def sms_notify(self, message):
        """
        充值失败则使用nexmo进行短信提醒
        """
        baseurl = "https://rest.nexmo.com/sms/json"
        balance = requests.get("https://rest.nexmo.com/account/get-balance", params={
            "api_key": KEY,
            "api_secret": SECERT,
        }).json()["value"]
        requests.get(baseurl, params={
            "api_key": KEY,
            "api_secret": SECERT,
            "from": "xxxx",
            "type": "unicode",
            "to": my_phone_number,
            "text": u'nexmo余额为{}, {}'.format(balance, unicode(message, 'UTF-8'))})


    def send_request(self, rechargetype, timeout=60, retry=3, **kwargs):
        """
        发送请求，获取数据成功则返回消息体，如果失败直接返回False
        """
        baseurl = "http://api.huafeiduo.com/gateway.cgi"
        #签名算法
        #传入参数字典→排序→键值对相加组成字符串→加上安全码→进行MD5运算
        kwargs.update({'api_key': API_KEY})
        sign = md5(''.join(sorted([''.join(i) for i in kwargs.iteritems()])) + SECRET_KEY).hexdigest()
        params = {
            "mod": rechargetype,
            "sign": sign,
            "api_key": API_KEY
        }
        params.update(kwargs)
        i = 0
        while i < retry:
            try:
                info = requests.get(baseurl, params=params, timeout=timeout)
                if info.status_code == 200:
                    if rechargetype == "order.phone.submit":     #简直是坑爹的特例
                        return info.json()["order_id"] if info.json()["status"] == "success" else False
                    print info.json()
                    return info.json()["data"] if info.json()["status"] == "success" else False
            except:
                pass
            time.sleep(10)
            i += 1
        return False

    def check_balance(self):
        """返回假或者余额"""
        blance = self.send_request("account.balance")
        return blance and blance["balance"]

    def optional_money(self):
        """
        依次查询可充值金额，返回第一个值或假
        """
        for i in self.money:
            if self.send_request("order.phone.check", card_worth=str(i), phone_number=str(telephone_number)):
                return unicode(i)
        return False

    def submit_time(self):
        hour = random.randint(8, 22)
        minute = random.randint(0, 60)
        return hour, minute

    def submit(self, telephone_number=telephone_number):
        money = self.optional_money()
        print money, type(money)
        if self.check_balance() < money + 0.5:
            self.sms_notify("huafeiduo余额不足,请充值")
            sys.exit()
        order_id = self.send_request("order.phone.submit",
                                     card_worth=money,
                                     phone_number=telephone_number,
                                     sp_order_id=''.join([str(random.randint(0, 9)) for k in range(15)])
        )
        print u"在{}尝试给{)充值{}元".format(time.strftime("%H:%M", time.gmtime(time.time() + 8 * 3600)),
                                      telephone_number,
                                      money
        )
        return order_id

    def check_order(self, order_id):
        #仅捕捉充值出错的情况发送短信提醒
        order_info = self.send_request("order.phone.get", order_id=order_id)
        if not order_id:
            self.sms_notify("我艹，为何充值会出我我真不造")


def main(recharge=recharge):
    recharge = recharge()
    flag = int(time.strftime("%d", time.gmtime(time.time() + 8 * 3600)))
    hour, minute = recharge.submit_time()
    while True:
        time.sleep(10)
        nowday = int(time.strftime("%d", time.gmtime(time.time() + 8 * 3600)))
        now_hour, now_minute = time.strftime("%H %M", time.gmtime(time.time() + 8 * 3600)).split()
        if flag == nowday:
            if int(now_hour) + int(now_minute) / 60.0 >= hour + minute / 60.0:
                order_id = recharge.submit()
                if not order_id:
                    recharge.sms_notify("huafeiduo余额充足但是莫名其妙的充值失败，请手动检查")
                else:
                    recharge.check_order(order_id)
                flag = nowday + 1
                hour, minute = recharge.submit_time()


if __name__ == "__main__":
    main()