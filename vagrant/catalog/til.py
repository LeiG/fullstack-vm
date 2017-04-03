#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base, User, Topic, Card

app = Flask(__name__)


engine = create_engine('sqlite:///til.db')
Base.metadata.bind = engine

db_session = sessionmaker(bind=engine)
session = db_session()


@app.route('/')
@app.route('/topics')
def Topics():
    all_topics = session.query(Topic).all()
    latest_cards =\
        session.query(Card).order_by(Card.updated_date.desc()).limit(10).all()

    return "This is the /topics page"


@app.route('/topics/new')
def NewTopic():
    return "This is the /topics/new page"


@app.route('/topics/<int:topic_id>/edit')
def EditTopic(topic_id):
    return "This is the /topics/%s/edit page" % str(topic_id)


@app.route('/topics/<int:topic_id>/delete')
def DeleteTopic(topic_id):
    return "This is the /topics/%s/delete page" % str(topic_id)


@app.route('/topics/<int:topic_id>/cards')
def Cards(topic_id):
    return "This is the /topics/%s/cards page" % str(topic_id)


@app.route('/topics/<int:topic_id>/cards/new')
def NewCard(topic_id):
    return "This is the /topics/%s/cards/new page" % str(topic_id)


@app.route('/topics/<int:topic_id>/cards/<int:card_id>/edit')
def EditCard(topic_id, card_id):
    return "This is the /topics/%s/cards/%s/edit page" % (str(topic_id), str(card_id))


@app.route('/topics/<int:topic_id>/cards/<int:card_id>/delete')
def DeleteCard(topic_id, card_id):
    return "This is the /topics/%s/cards/%s/delete page" % (str(topic_id), str(card_id))


if __name__ == "__main__":
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
