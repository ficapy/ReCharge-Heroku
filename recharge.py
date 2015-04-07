#!/usr/bin/env python
# -*- coding: utf-8 -*-
#Create on:2015.1.19

"""
某日答应某人每天给冲1元话费，于是就写了这个0_0
流程为检测可充值金额及余额，如若余额大于金额则提交订单充值获取订单号
由订单号查询充值状态，若首次检查非失败状态则认为充值成功，若失败则发送
短信给俺
"""

import requests
from hashlib import md5
import time, datetime
import random
import logging
from db import ReChargeLog
from db import TimeSign
import json
from sms import sendMsg

with open(r'./cfg.json', 'r') as f:
    cfg = json.load(f)

###huafeiduo API
API_KEY = cfg["huafeiduo"]["API_KEY"]
SECRET_KEY = cfg["huafeiduo"]["SECRET_KEY"]
telephone_number = cfg["huafeiduo"]["telephone_number"]


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
        ReChargeLog.savemsg(self.format(record))


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
    def __init__(self, money=(1, 2, 5, 10, 20, 50, 100, 300), limit_money=2, optional_money_circle_time=4):
        self.money = money
        self.session = requests.Session()
        self.limit_money = limit_money
        self.optional_money_circle_time = optional_money_circle_time


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
        无限循环查询可充值金额，返回第一个值
        """
        for i in self.money:
            if self.send_request("order.phone.check", card_worth=str(i), phone_number=str(telephone_number)):
                return i
        if random.random() >0.5:sendMsg("充值脚本","网络故障？没有查询到可充值的金额")
        return self.optional_money()

    def submit_time(self):
        hour = random.randint(0, 9)  #换算为GTM+8为（8,17）
        minute = random.randint(0, 59)
        return datetime.datetime.now().replace(hour=hour, minute=minute)

    def submit(self, telephone_number=telephone_number):
        """
        对不起啊，我是个穷人，限定到有2元可以充值的时候充值
        更具下面随机生成的时间最晚是晚上7点，保险起见设置4个小时内查询是否有满足条件的金额
        所以最多使用4*3600/10次查询,如果运气不好...那么听天由命吧
        如果充值超过限值，那么未来几天就暂停充值一段时间
        """
        start = time.time()
        while datetime.timedelta(seconds=int(time.time()-start)) < datetime.timedelta(hours=self.optional_money_circle_time):
            money = self.optional_money()
            if money <= self.limit_money:
                log.debug("花擦居然刷新了{}小时才刷到合适的价格".format(datetime.timedelta(seconds=int(time.time()-start)).total_seconds() / 3600))
                break
            time.sleep(60)
        if money > self.limit_money:
            log.debug("辛苦你了亲，居然连刷4个小时都没刷到")

        if self.check_balance() < money + 0.5:
            log.warning("huafeiduo余额不足,速速充值")
            sendMsg("充值脚本","huafeiduo余额不足,速速充值")
        order_id = self.send_request("order.phone.submit",
                                     card_worth=str(money),
                                     phone_number=telephone_number,
                                     sp_order_id=''.join([str(random.randint(0, 9)) for k in range(15)])
        )
        log.info("尝试给{}充值{}元".format(telephone_number, money))
        return order_id, money

    def check_order(self, order_id):
        #如果订单号返回failure、订单状态若返回成功失败之外则查询六次每次5分钟，30分钟后还没有返回则认为此次充值失败
        order_info = self.send_request("order.phone.get", order_id=str(order_id))
        if not order_info or order_info["status"] == u'failure':
            log.error("我艹，为何充值会出错我真不造,重试一次吧")
            return False
        elif order_info["status"] == u'success':
            return True
        else:
            for i in xrange(6):
                time.sleep(60 * 5)
                order_status = self.send_request("order.phone.get", order_id=str(order_id))["status"]
                if order_status == u"success":
                    log.info("充值成功")
                    return True
                elif order_status == u'failure':
                    return False
            return False


def main(recharge=ReCharge):
    recharge = recharge()
    default_optional_money_circle_time = recharge.optional_money_circle_time
    log.info('丫又重启了，新的一天开始咯')
    log.info("马上开始充值呀") if TimeSign.gettime() < datetime.datetime.utcnow() else\
        log.info('等吧等吧，{}号{}时{}分就进行充值啦'.format(
            (TimeSign.gettime()+datetime.timedelta(hours=8)).day,
            (TimeSign.gettime()+datetime.timedelta(hours=8)).hour,
            (TimeSign.gettime()+datetime.timedelta(hours=8)).minute,
                ))
    while True:
        time.sleep(10)
        if TimeSign.fight():
            order_id, money = recharge.submit()
            #查询订单状态最多阻塞30分钟
            order_status = recharge.check_order(order_id)
            #如果失败最大的可能为查询是可以，但是充值金额不满足，此情况重新循环
            #并且将查询循环时间改成半小时，成功后恢复到4小时
            if not order_status:
                recharge.optional_money_circle_time = 0.5
                log.error("金额为{}订单{}充值失败！！！".format(str(money), str(order_id)))
            else:
                recharge.optional_money_circle_time = default_optional_money_circle_time
                days = 1 if money < 2 else int((money - 2) / 2)
                next_time = recharge.submit_time() + datetime.timedelta(days=days)
                TimeSign.settime(next_time)
                next_time_gtm8 = next_time + datetime.timedelta(hours=8)
                log.info('等吧等吧，{}号{}时{}分就进行下次充值啦'.format(
                    next_time_gtm8.day,
                    next_time_gtm8.hour,
                    next_time_gtm8.minute,
                ))


if __name__ == "__main__":
    main()