#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy import create_engine


Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String(80), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))
    provider = Column(String(80))


class Company(Base):
    __tablename__ = 'company'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    created_date = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id': self.id,
            'name': self.name,
            'user_id': self.user_id,
            'created_date': self.created_date,
        }


class Card(Base):
    __tablename__ = 'card'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    content = Column(Text, nullable=False)
    created_date = Column(DateTime(timezone=True), server_default=func.now())
    updated_date = Column(DateTime(timezone=True), onupdate=func.now())
    company_id = Column(Integer, ForeignKey('company.id'))
    company = relationship(
        Company, backref=backref('card', cascade='all, delete')
    )
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id': self.id,
            'name': self.name,
            'content': self.content,
            'user_id': self.user_id,
            'company_id': self.company_id,
            'created_date': self.created_date,
            'updated_date': self.updated_date,
        }



def init_db():
    engine = create_engine('sqlite:///techview.db')

    Base.metadata.create_all(engine)


if __name__ == "__main__":
    init_db()
