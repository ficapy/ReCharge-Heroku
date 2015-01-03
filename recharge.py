#!/usr/bin/env python
# -*- coding: utf-8 -*-
#Create on:2015.1.1
#Version:0.1.4

"""
某日答应某人每天给冲1元话费，于是就写了这个0_0
流程为检测可充值金额及余额，如若余额大于金额则提交订单充值获取订单号
由订单号查询充值状态，若首次检查非失败状态则认为充值成功，若失败则发送
短信给俺
"""

import requests
from hashlib import md5
import time
import random
import logging
from db import msg

###huafeiduo API
API_KEY = "-----------------------------------------"
SECRET_KEY = "--------------------------------------"
telephone_number = "--------------------------------"

###nexmo API
KEY = "---------------------------------------------"
SECERT = "------------------------------------------"
my_phone_number = "---------------------------------"  ###注意此处需要添加国际区号，但不用添加"+"号

#设置时区Unix Only
import platform
import os

if time.timezone != -28800:
    if platform.uname()[0] == "Linux":
        os.environ['TZ'] = "Asia/Shanghai"
        time.tzset()
    elif platform.uname()[0] == "Windows":
        pass

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
format = "%(asctime)s %(filename)s [line:%(lineno)d] %(levelname)s %(message)s"
datefmt = "%Y年%m月%d日 %H时%M分%S秒"
formatter = logging.Formatter(format, datefmt=datefmt)
#输出log到数据库
class DBHandler(logging.Handler): # Inherit from logging.Handler
    def __init__(self):
        logging.Handler.__init__(self)

    def emit(self, record):
        msg(self.format(record))


dbhandler = DBHandler()
dbhandler.setLevel(logging.INFO)
dbhandler.setFormatter(formatter)
log.addHandler(dbhandler)
#输出到屏幕
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.NOTSET)
console_handler.setFormatter(formatter)
log.addHandler(console_handler)


class ReCharge(object):
    def __init__(self, money=(1, 2, 5, 10, 20, 50, 100, 300)):
        self.money = money
        self.session = requests.Session()

    def sms_notify(self, message):
        """
        充值失败则使用nexmo进行短信提醒
        """
        log.error("充值失败，发送短信提醒")
        baseurl = "https://rest.nexmo.com/sms/json"
        balance = self.session.get("https://rest.nexmo.com/account/get-balance", params={
            "api_key": KEY,
            "api_secret": SECERT,
        }).json()["value"]
        self.session.get(baseurl, params={
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
        sign = md5(''.join(sorted(''.join(i) for i in kwargs.iteritems())) + SECRET_KEY).hexdigest()
        params = {
            "mod": rechargetype,
            "sign": sign,
            "api_key": API_KEY
        }
        params.update(kwargs)
        for i in xrange(retry):
            try:
                info = self.session.get(baseurl, params=params, timeout=timeout)
                if info.status_code == 200:
                    if rechargetype == "order.phone.submit":     #简直是坑爹的特例
                        return info.json()["order_id"] if info.json()["status"] == "success" else False
                    return info.json()["data"] if info.json()["status"] == "success" else False
            except Exception as e:
                log.warning("请求{}时失败，参数为：{} 异常情况为{}".format(rechargetype, kwargs, e))
            time.sleep(10)
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
                return i
        return False

    def submit_time(self):
        hour = random.randint(8, 17)
        minute = random.randint(0, 60)
        return hour, minute

    def submit(self, telephone_number=telephone_number, limit_money=2):
        """
        对不起啊，我是个穷人，限定到有2元可以充值的时候充值
        更具下面随机生成的时间最晚是晚上7点，保险起见设置4个小时内查询是否有满足条件的金额
        所以最多使用4*3600/10次查询,如果运气不好...那么听天由命吧
        如果充值超过限值，那么未来几天就暂停充值一段时间
        """
        for i in xrange(4 * 3600 / 60):
            money = self.optional_money()
            if money <= limit_money:
                log.debug("花擦居然刷新了{}小时才刷到合适的价格".format(i * 10.0 / 3600))
                break
            time.sleep(60)
        if money > limit_money:
            log.debug("辛苦你了亲，居然连刷4个小时都没刷到")

        if self.check_balance() < money + 0.5:
            log.warning("huafeiduo余额不足,速速充值")
            self.sms_notify("huafeiduo余额不足,速速充值")
        order_id = self.send_request("order.phone.submit",
                                     card_worth=str(money),
                                     phone_number=telephone_number,
                                     sp_order_id=''.join([str(random.randint(0, 9)) for k in range(15)])
        )
        log.info("尝试给{}充值{}元".format(telephone_number, money))
        return order_id, money

    def check_order(self, order_id):
        #如果订单号返回failure、订单状态若返回成功失败之外则查询三次每次10分钟，30分钟后还没有返回则认为此次充值失败
        order_info = self.send_request("order.phone.get", order_id=str(order_id))
        if not order_info or order_info["status"] == u'failure':
            log.error("我艹，为何充值会出错我真不造,重试一次吧")
            return False
        elif order_info["status"] == u'success':
            return True
        else:
            for i in xrange(3):
                time.sleep(60 * 10)
                order_status = self.send_request("order.phone.get", order_id=str(order_id))["status"]
                if order_status == u"success":
                    log.info("充值成功")
                    return True
                elif order_status == u'failure':
                    return False
            return False


def main(recharge=ReCharge):
    recharge = recharge()
    flag = int(time.strftime("%d", time.gmtime(time.time() + 8 * 3600)))
    hour, minute = 0, 0   #首次测试用，可同时设置limit_money为10
    # hour, minute = recharge.submit_time()
    log.info('等吧等吧，到{}时{}分就解放啦'.format(hour, minute))
    done = False
    while True:
        time.sleep(10)
        nowday, epoch = int(time.strftime("%d", time.gmtime(time.time() + 8 * 3600))), time.time() + 8 * 3600
        now_hour, now_minute = time.strftime("%H %M", time.gmtime(time.time() + 8 * 3600)).split()
        if not done:
            flag = nowday
        if flag == nowday:
            if int(now_hour) + int(now_minute) / 60.0 >= hour + minute / 60.0:
                order_id, money = recharge.submit()
                #查询订单状态最多阻塞30分钟
                order_status = recharge.check_order(order_id)
                #如果失败最大的可能为查询是可以，但是充值金额不满足，此情况重新循环
                if not order_status:
                    done = False
                    log.error("充值失败！！！")
                else:
                    if money > 2:
                        done = True
                        flag = int(time.strftime("%d", time.gmtime(epoch + (money - 2) / 2 * 24 * 3600)))
                    else:
                        # 日期推后一天
                        done = True
                        flag = int(time.strftime("%d", time.gmtime(epoch + 24 * 3600)))
                    hour, minute = recharge.submit_time()
                    log.debug('等吧等吧，{}号{}时{}分就进行下次充值啦'.format(flag, hour, minute))


if __name__ == "__main__":
    main()