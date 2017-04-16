#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask
from flask import render_template
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base, User, Company, Card
import fake_data

app = Flask(__name__)


engine = create_engine('sqlite:///techview.db')
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
@app.route('/companies/')
def showCompanies():
    # all_topics = session.query(Topic).all()
    # latest_cards =\
    #     session.query(Card).order_by(Card.updated_date.desc()).limit(10).all()

    return render_template(
        'companies.html',
        all_companies=fake_data.companies,
        all_cards=fake_data.cards,
    )


@app.route('/companies/new/', methods=['GET', 'POST'])
def newCompany():
    return render_template(
        'new-company.html',
        all_companies=fake_data.companies,
    )


@app.route('/companies/<int:company_id>/edit/', methods=['GET', 'POST'])
def editCompany(company_id):
    return render_template(
        'edit-company.html',
        all_companies=fake_data.companies,
        company=fake_data.company,
    )


@app.route('/companies/<int:company_id>/delete/', methods=['GET', 'POST'])
def deleteCompany(company_id):
    return render_template(
        'delete-company.html',
        all_companies=fake_data.companies,
        company=fake_data.company,
    )


@app.route('/companies/<int:company_id>/')
@app.route('/companies/<int:company_id>/cards/')
def showCards(company_id):
    return render_template(
        'cards.html',
        all_companies=fake_data.companies,
        company=fake_data.company,
        company_cards=fake_data.cards,
    )


@app.route('/companies/<int:company_id>/cards/new/')
def newCard(company_id):
    return render_template(
        'new-card.html',
        all_companies=fake_data.companies,
        company=fake_data.company,
    )


@app.route('/companies/<int:company_id>/cards/<int:card_id>/edit/')
def editCard(company_id, card_id):
    return render_template(
        'edit-card.html',
        all_companies=fake_data.companies,
        company=fake_data.company,
        card=fake_data.card,
    )


@app.route('/companies/<int:company_id>/cards/<int:card_id>/delete/')
def deleteCard(company_id, card_id):
    return render_template(
        'delete-card.html',
        all_companies=fake_data.companies,
        card=fake_data.card,
    )


if __name__ == "__main__":
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
