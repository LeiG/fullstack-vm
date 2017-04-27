#!/usr/bin/env python
# -*- coding: utf-8 -*-

import httplib2
import json
import random
import requests
import string

from flask import\
    Flask, make_response, redirect, request, render_template, flash
from flask import session as login_session

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from oauth2client.client import flow_from_clientsecrets, FlowExchangeError

from database_setup import Base, User, Company, Card
import fake_data

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read()
)['web']['client_id']

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super secret key'

engine = create_engine('sqlite:///techview.db')
Base.metadata.bind = engine

db_session = sessionmaker(bind=engine)
session = db_session()


@app.route('/login/', methods=['GET', 'POST'])
def login():
    state = ''.join(
        random.choice(string.ascii_uppercase + string.digits)
        for _ in xrange(32)
    )
    login_session['state'] = state

    return render_template('login.html')


@app.route('/gconnect/', methods=['POST'])
def gconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state token'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    code = request.data
    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code'),
            401,
        )
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check the access token is valid
    access_token = credentials.access_token
    url = (
        'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
        % access_token
    )
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify the access token is used for intended user
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps('Token\'s user ID doesn\'t match given user ID '), 401
        )
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify the access token is valid for this app
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps('Token\'s client ID doesn\'t match given application'),
            401,
        )
        response.headers['Content-Type'] = 'application/json'
        return response

    # check if user is already logged in
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected'), 200
        )
        response.headers['Content-Type'] = 'application/json'

    # store the access token in the session for later use
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = request.get(userinfo_url, params=params)
    data = json.loads(answer.text)

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    flash('You are now logged in as %s' % login_session['username'])

    return


@app.route('/gdisconnect/')
def gdisconnect():
    # Only disconnect a connected user
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(json.dumps('Current user not connected'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Execute HTTP GET request to revoke current token
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(
            json.dumps('Failed to revoke token for given user.'),
            400,
        )
        response.headers['Content-Type'] = 'application/json'
        return response


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
    if 'username' not in login_session:
        return redirect('/login/')

    if request.method == 'POST':
        return render_template(
            'new-company.html',
            all_companies=fake_data.companies,
        )


@app.route('/companies/<int:company_id>/edit/', methods=['GET', 'POST'])
def editCompany(company_id):
    if 'username' not in login_session:
        return redirect('/login/')

    return render_template(
        'edit-company.html',
        all_companies=fake_data.companies,
        company=fake_data.company,
    )


@app.route('/companies/<int:company_id>/delete/', methods=['GET', 'POST'])
def deleteCompany(company_id):
    if 'username' not in login_session:
        return redirect('/login/')

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
    if 'username' not in login_session:
        return redirect('/login/')

    return render_template(
        'new-card.html',
        all_companies=fake_data.companies,
        company=fake_data.company,
    )


@app.route('/companies/<int:company_id>/cards/<int:card_id>/edit/')
def editCard(company_id, card_id):
    if 'username' not in login_session:
        return redirect('/login/')

    return render_template(
        'edit-card.html',
        all_companies=fake_data.companies,
        company=fake_data.company,
        card=fake_data.card,
    )


@app.route('/companies/<int:company_id>/cards/<int:card_id>/delete/')
def deleteCard(company_id, card_id):
    if 'username' not in login_session:
        return redirect('/login/')

    return render_template(
        'delete-card.html',
        all_companies=fake_data.companies,
        card=fake_data.card,
    )


if __name__ == "__main__":
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
