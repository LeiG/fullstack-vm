#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine


Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String(80), nullable=False)
    email = Column(String(250), nullable=False)


class Topic(Base):
    __tablename__ = 'topic'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    created_date = Column(DateTime(timezone=True), server_default=func.now())


class Card(Base):
    __tablename__ = 'card'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    content = Column(Text, nullable=False)
    created_date = Column(DateTime(timezone=True), server_default=func.now())
    updated_date = Column(DateTime(timezone=True), onupdate=func.now())
    topic_id = Column(Integer, ForeignKey('topic.id'))
    topic = relationship(Topic)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)


def init_db():
    engine = create_engine('sqlite:///til.db')

    Base.metadata.create_all(engine)


if __name__ == "__main__":
    init_db()
