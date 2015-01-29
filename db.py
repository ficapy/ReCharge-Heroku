#!/usr/bin/env python
# -*- coding: utf-8 -*-
#Create on:2015.1.19

"""
因为heroku无法进行本地存储和读取，所有选择用数据库存储记录数据
→_→其实数据库也有只能保存1W行数据的限制
"""

import os
import urlparse
from sqlalchemy import Column, DateTime, Integer, create_engine,Boolean,String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class TimeSign(Base):
    __tablename__ = 'time_sign'
    id = Column(Integer, primary_key=True)
    ts = Column(DateTime, default=datetime.utcnow())

    @staticmethod
    def gettime():
        return s.query(TimeSign).first().ts


    @staticmethod
    def settime(time=datetime.utcnow()):
        s.query(TimeSign).update({"ts": time})
        s.commit()


    @staticmethod
    def fight():
        #datetime.datetime.now()>datetime.datetime.utcnow() + datetime.timedelta(hours=1)→True
        #统一使用UTC
        if datetime.utcnow() > TimeSign.gettime() and 0 <= datetime.utcnow().hour <= 9:
            return True
        return False

class ReChargeLog(Base):
    __tablename__ = 'ReChargeLog'
    id = Column(Integer, primary_key=True)
    msg = Column(String)

    @staticmethod
    def savemsg(message):
        d = ReChargeLog(msg=message)
        s.add(d)
        s.commit()


#方便本地测试
if "DATABASE_URL" in list(os.environ):
    urlparse.uses_netloc.append("postgres")
    url = urlparse.urlparse(os.environ["DATABASE_URL"])
    engine = create_engine('postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{database}'.format(database=url.path[1:],
                                                                                                user=url.username,
                                                                                                pwd=url.password,
                                                                                                host=url.hostname,
                                                                                                port=url.port))
else:
    engine = create_engine('postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{database}'.format(database="test",
                                                                                                user="test_postgres",
                                                                                                pwd="123456",
                                                                                                host="localhost",
                                                                                                port=5432))
session = sessionmaker()
session.configure(bind=engine)
Base.metadata.create_all(engine)
s = session()
#设置初始时间
if not s.query(TimeSign).first():
    inittime = TimeSign()
    s.add(inittime)
    s.commit()
