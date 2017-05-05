#!/usr/bin/env python
# -*- coding: utf-8 -*-

import httplib2
import json
import random
import string

from flask import\
    Flask, make_response, redirect, request, \
    render_template, flash, url_for, session

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from oauth2client.client import flow_from_clientsecrets, FlowExchangeError

import utils
from database_setup import Base, Company, Card
import fake_data

CLIENT_ID = json.loads(
    open('g_client_secrets.json', 'r').read()
)['web']['client_id']

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super secret key'

engine = create_engine('sqlite:///techview.db')
Base.metadata.bind = engine

db_session = sessionmaker(bind=engine)()


@app.route('/login/', methods=['GET', 'POST'])
def login():
    state = ''.join(
        random.choice(string.ascii_uppercase + string.digits)
        for _ in xrange(32)
    )
    session['state'] = state

    return render_template('login.html')


@app.route('/gconnect/', methods=['POST'])
def gconnect():
    if request.args.get('state') != session['state']:
        response = make_response(json.dumps('Invalid state token'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    code = request.data
    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('g_client_secrets.json', scope='')
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
    stored_credentials = session.get('credentials')
    stored_gplus_id = session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected'), 200
        )
        response.headers['Content-Type'] = 'application/json'

    # store the access token in the session for later use
    session['credentials'] = credentials
    session['gplus_id'] = gplus_id

    # get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = request.get(userinfo_url, params=params)
    data = json.loads(answer.text)

    session['provider'] = 'Google'
    session['username'] = data['name']
    session['picture'] = data['picture']
    session['email'] = data['email']

    # store user info into db
    if utils.get_user_id_by_email(data['email'], db_session) is None:
        utils.create_user(session, db_session)

    flash('You are now logged in as %s' % session['username'])

    return redirect(url_for('showCompanies'))


@app.route('/fbconnect/', methods=['POST'])
def fbconnect():
    if request.args.get('state') != session['state']:
        response = make_response(json.dumps('Invalid state token'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    access_token = request.data
    # Exchange client token for long-lived server-side token
    app_id = json.loads(
        open('fb_client_secrets.json', 'r').read()
    )['web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read()
    )['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/' \
        'access_token?grant_type=fb_exchange_token&' \
        'client_id=%s&client_secret=%s&fb_exchange_token=%s' \
        % (app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info
    token = result.split('&')[0]
    userinfo_url = \
        'https://graph.facebook.com/v2.8/me?%s&fields=name,id,email' \
        % token
    h = httplib2.Http()
    result = h.request(userinfo_url, 'GET')[1]
    data = json.loads(result)
    session['provider'] = 'Facebook'
    session['username'] = data['name']
    session['email'] = data['email']
    session['facebook_id'] = data['id']

    # The token must be stored in the session in order to properly logout
    stored_token = token.split("=")[1]
    session['access_token'] = stored_token

    # Get user picture
    userpic_url = \
        'https://graph.facebook.com/v2.8/me/picture?%s' \
        '&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(userpic_url, 'GET')[1]
    data = json.loads(result)

    session['picture'] = data['data']['url']

    # store user into db
    if utils.get_user_id_by_email(data['email'], db_session) is None:
        utils.create_user(session, db_session)

    flash('You are now logged in as %s' % session['username'])

    return redirect(url_for('showCompanies'))


@app.route('/logout/', methods=['GET', 'POST'])
def logout():
    if session['provider'] is None:
        response = make_response(json.dumps('Current user not logged in'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        if session['provider'] == 'Google' and \
           gdisconnect()['status'] == '200':
            del session['credentials']
            del session['gplus_id']

        elif session['provider'] == 'Facebook' and \
             fbdisconnect()['status'] == '200':
            del session['facebook_id']
            del session['access_token']

        else:
            response = make_response(
                json.dumps('Failed to revoke token for given user.'),
                400,
            )
            response.headers['Content-Type'] = 'application/json'
            return response

        del session['username']
        del session['email']
        del session['picture']
        del session['provider']

        flash('You have successfully been logged out.')

        return redirect(url_for('showCompanies'))


@app.route('/gdisconnect/')
def gdisconnect():
    credentials = session.get('credentials')

    # Execute HTTP GET request to revoke current token
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    return result


@app.route('/fbdisconnect/')
def fbdisconnect():
    facebook_id = session['facebook_id']

    # The access token must me included to successfully logout
    access_token = session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' \
          % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]

    return result


@app.route('/')
@app.route('/companies/')
def showCompanies():
    all_companies = db_session.query(Company).all()
    latest_cards =\
        db_session.query(Card).order_by(Card.updated_date.desc()).limit(10).all()

    return render_template(
        'companies.html',
        all_companies=all_companies,
        all_cards=latest_cards,
    )


@app.route('/companies/new/', methods=['GET', 'POST'])
def newCompany():
    if 'username' not in session:
        flash('You need to login to add company.')
        return redirect('/login/')

    if request.method == 'POST':
        new_company_name = request.args.get('newCompany')

        if new_company_name is None or new_company_name == '':
            flash('Please enter a valid company name.')
        elif db_session.query(Company)\
                    .filter(name == new_company_name).count() > 0:
            flash('%s already exists.' % new_company_name)
        else:
            new_company = Company(name=new_company_name)
            db_session.add(new_company)
            db_session.commit()

            return redirect(url_for('showCompanies'))

    all_companies = db_session.query(Company).all()

    return render_template(
        'new-company.html',
        all_companies=all_companies,
    )


@app.route('/companies/<int:company_id>/edit/', methods=['GET', 'POST'])
def editCompany(company_id):
    if 'username' not in session:
        flash('You need to login to edit company.')
        return redirect('/login/')

    company = utils.get_company_by_id(company_id, db_session)

    if company is None:
        flash('Company does not exist')
        return redirect(url_for('showCompanies'))

    elif request.method == 'POST':
        new_company_name = request.form.get('newCompany')

        if new_company_name is None or new_company_name == '':
            flash('Please enter a valid company name.')
        else:
            company.name = new_company_name
            db_session.add(company)
            db_session.commit()

    all_companies = db_session.query(Company).all()

    return render_template(
        'edit-company.html',
        all_companies=all_companies,
        company=company,
    )


@app.route('/companies/<int:company_id>/delete/', methods=['GET', 'POST'])
def deleteCompany(company_id):
    if 'username' not in session:
        flash('You need to login to delete company.')
        return redirect('/login/')

    company = utils.get_company_by_id(company_id, db_session)

    if company is None:
        flash('Company does not exist')
        return redirect(url_for('showCompanies'))

    elif request.method == 'POST':
        pass

    all_companies = db_session.query(Company).all()

    return render_template(
        'delete-company.html',
        all_companies=all_companies,
        company=company,
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
    if 'username' not in session:
        return redirect('/login/')

    return render_template(
        'new-card.html',
        all_companies=fake_data.companies,
        company=fake_data.company,
    )


@app.route('/companies/<int:company_id>/cards/<int:card_id>/edit/')
def editCard(company_id, card_id):
    if 'username' not in session:
        return redirect('/login/')

    return render_template(
        'edit-card.html',
        all_companies=fake_data.companies,
        company=fake_data.company,
        card=fake_data.card,
    )


@app.route('/companies/<int:company_id>/cards/<int:card_id>/delete/')
def deleteCard(company_id, card_id):
    if 'username' not in session:
        return redirect('/login/')

    return render_template(
        'delete-card.html',
        all_companies=fake_data.companies,
        card=fake_data.card,
    )


if __name__ == "__main__":
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
