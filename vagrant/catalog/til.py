#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask
from flask import render_template
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base, User, Topic, Card
import fake_data

app = Flask(__name__)


engine = create_engine('sqlite:///til.db')
Base.metadata.bind = engine

db_session = sessionmaker(bind=engine)
session = db_session()


@app.route('/login/', methods=['GET', 'POST'])
def login():
    return render_template('login.html')


@app.route('/signup/', methods=['GET', 'POST'])
def signup():
    return render_template('signup.html')


@app.route('/logout/', methods=['GET', 'POST'])
def logout():
    return "You logged out..."


@app.route('/')
@app.route('/topics/')
def showTopics():
    # all_topics = session.query(Topic).all()
    # latest_cards =\
    #     session.query(Card).order_by(Card.updated_date.desc()).limit(10).all()

    return render_template(
        'topics.html',
        all_topics=fake_data.topics,
        all_cards=fake_data.cards,
    )


@app.route('/topics/new/', methods=['GET', 'POST'])
def newTopic():
    return render_template('new-topic.html', all_topics=fake_data.topics)


@app.route('/topics/<int:topic_id>/edit/', methods=['GET', 'POST'])
def editTopic(topic_id):
    return render_template(
        'edit-topic.html',
        all_topics=fake_data.topics,
        topic=fake_data.topic,
    )


@app.route('/topics/<int:topic_id>/delete/', methods=['GET', 'POST'])
def deleteTopic(topic_id):
    return render_template(
        'delete-topic.html',
        all_topics=fake_data.topics,
        topic=fake_data.topic,
    )


@app.route('/topics/<int:topic_id>/')
@app.route('/topics/<int:topic_id>/cards/')
def showCards(topic_id):
    return render_template(
        'cards.html',
        all_topics=fake_data.topics,
        topic=fake_data.topic,
        topic_cards=fake_data.cards,
    )


@app.route('/topics/<int:topic_id>/cards/new/')
def newCard(topic_id):
    return render_template(
        'new-card.html',
        all_topics=fake_data.topics,
        topic=fake_data.topic,
    )


@app.route('/topics/<int:topic_id>/cards/<int:card_id>/edit/')
def editCard(topic_id, card_id):
    return render_template(
        'edit-card.html',
        all_topics=fake_data.topics,
        topic=fake_data.topic,
        card=fake_data.card,
    )


@app.route('/topics/<int:topic_id>/cards/<int:card_id>/delete/')
def deleteCard(topic_id, card_id):
    return render_template(
        'delete-card.html',
        all_topics=fake_data.topics,
        card=fake_data.card,
    )


if __name__ == "__main__":
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
