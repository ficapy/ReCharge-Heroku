#!/usr/bin/env python
# -*- coding: utf-8 -*-
#Create on:2015.1.3
#Version:0.0.1

"""
因为heroku无法进行本地存储和读取，所有选择用数据库存储记录数据
→_→其实数据库也有只能保存1W行数据的限制
"""

import os
import urlparse
from sqlalchemy import Column, String, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class ReChargeLog(Base):
    __tablename__ = 'ReChargeLog'
    id = Column(Integer, primary_key=True)
    msg = Column(String)

    def __init__(self, msg):
        self.msg = msg


urlparse.uses_netloc.append("postgres")
url = urlparse.urlparse(os.environ["DATABASE_URL"])
engine = create_engine('postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{database}'.format(database=url.path[1:],
                                                                                            user=url.username,
                                                                                            pwd=url.password,
                                                                                            host=url.hostname,
                                                                                            port=url.port))
session = sessionmaker()
session.configure(bind=engine)
Base.metadata.create_all(engine)
s = session()


def msg(msg):
    d = ReChargeLog(msg)
    s.add(d)
    s.commit()