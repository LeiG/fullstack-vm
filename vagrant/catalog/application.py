#!/usr/bin/env python
# -*- coding: utf-8 -*-

import httplib2
import json
import requests
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


@app.route('/login/', methods=['GET'])
def login():
    state = ''.join(
        random.choice(string.ascii_uppercase + string.digits)
        for _ in xrange(32)
    )
    session['state'] = state

    error = request.args.get('error', '')

    return render_template('login.html', STATE=state, error=error)


@app.route('/gconnect', methods=['POST'])
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
    session['access_token'] = credentials.access_token
    session['gplus_id'] = gplus_id

    # get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = json.loads(answer.text)

    session['provider'] = 'Google'
    session['username'] = data['name']
    session['picture'] = data['picture']
    # email is working inconsistently for oauth2 endpoint
    # use https://www.googleapis.com/plus/v1/people/me instead if it is needed
    session['email'] = data.get('emails', gplus_id + "@google.com")

    # store user info into db
    if utils.get_user_by_email(session['email'], db_session) is None:
        utils.create_user(session, db_session)

    flash('You are now logged in as %s' % session['username'])

    return redirect(url_for('showCompanies'))


@app.route('/fbconnect', methods=['POST'])
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
    token = json.loads(result)['access_token']
    userinfo_url = \
        'https://graph.facebook.com/v2.8/me?access_token=%s' \
        '&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(userinfo_url, 'GET')[1]

    data = json.loads(result)

    session['provider'] = 'Facebook'
    session['username'] = data['name']
    # email can be empty
    # if someone signup with phone number or email is not confirmed
    # save as uid@facebook.com to hack around
    session['email'] = data.get('email', data['id'] + '@facebook.com')
    session['facebook_id'] = data['id']

    # The token must be stored in the session in order to properly logout
    session['access_token'] = token

    # Get user picture
    userpic_url = \
        'https://graph.facebook.com/v2.8/me/picture?access_token=%s' \
        '&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(userpic_url, 'GET')[1]
    data = json.loads(result)

    session['picture'] = data['data']['url']

    # store user into db
    if utils.get_user_id_by_email(session['email'], db_session) is None:
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
            del session['gplus_id']

        elif session['provider'] == 'Facebook' and \
             fbdisconnect()['success'] == True:
            del session['facebook_id']

        else:
            response = make_response(
                json.dumps('Failed to revoke token for given user.'),
                400,
            )
            response.headers['Content-Type'] = 'application/json'
            return response

        del session['access_token']
        del session['username']
        del session['email']
        del session['picture']
        del session['provider']

        return redirect(url_for('showCompanies'))


@app.route('/gdisconnect/')
def gdisconnect():
    # Execute HTTP GET request to revoke current token
    access_token = session.get('access_token')
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    response = h.request(url, 'GET')[0]
    print(response)

    return response


@app.route('/fbdisconnect/')
def fbdisconnect():
    facebook_id = session['facebook_id']

    # The access token must me included to successfully logout
    access_token = session['access_token']
    url = 'https://graph.facebook.com/v2.8/%s/permissions?access_token=%s' \
          % (facebook_id, access_token)

    h = httplib2.Http()
    result = json.loads(h.request(url, 'DELETE')[1])

    return result


@app.route('/')
@app.route('/companies/')
def showCompanies():
    all_companies = db_session.query(Company).all()
    latest_cards =\
        db_session.query(Card)\
                  .order_by(Card.updated_date.desc()).limit(10).all()

    return render_template(
        'companies.html',
        all_companies=all_companies,
        all_cards=latest_cards,
    )


@app.route('/companies/new/', methods=['GET', 'POST'])
def newCompany():
    if 'username' not in session:
        return redirect(
            url_for('login', error='You need to login to add company')
        )

    user = utils.get_user_by_email(session['email'], db_session)

    error = request.args.get('error', '')

    if request.method == 'POST':
        new_company_name = request.form.get('newCompany')

        if new_company_name is None or new_company_name == '':
            error = 'Please enter a valid company name'
        elif db_session.query(Company)\
                       .filter(Company.name==new_company_name).count() > 0:
            error = '%s already exists' % new_company_name
        else:
            new_company = Company(name=new_company_name, user_id=user.id)
            db_session.add(new_company)
            db_session.commit()

            return redirect(url_for('showCompanies'))

    all_companies = db_session.query(Company).all()

    return render_template(
        'new-company.html',
        all_companies=all_companies,
        error=error,
    )


@app.route('/companies/<int:company_id>/edit/', methods=['GET', 'POST'])
def editCompany(company_id):
    if 'username' not in session:
        return redirect(
            url_for('login', error='You need to login to edit company')
        )

    user = utils.get_user_by_email(session['email'], db_session)

    company = utils.get_company_by_id(company_id, db_session)

    error = request.args.get('error', '')

    if company is None:
        return redirect(url_for('showCompanies'))

    elif company.user_id != user.id:
        error = "You can only edit the companies you created"

    elif request.method == 'POST':
        new_company_name = request.form.get('newCompany')

        if new_company_name is None or new_company_name == '':
            error = 'Please enter a valid company name'
        else:
            company.name = new_company_name
            db_session.add(company)
            db_session.commit()

    all_companies = db_session.query(Company).all()

    return render_template(
        'edit-company.html',
        all_companies=all_companies,
        company=company,
        error=error,
    )


@app.route('/companies/<int:company_id>/delete/', methods=['GET', 'POST'])
def deleteCompany(company_id):
    if 'username' not in session:
        return redirect(
            url_for('login', error='You need to login to delete company')
        )

    user = utils.get_user_by_email(session['email'], db_session)

    company = utils.get_company_by_id(company_id, db_session)

    error = request.args.get('error', '')

    if company is None:
        return redirect(url_for('showCompanies'))

    elif company.user_id != user.id:
        error = "You can only delete companies you created"

    elif request.method == 'POST':
        if request.form.get('deleteCompany'):
            db_session.delete(company)
            db_session.commit()
            return redirect(url_for('showCompanies'))

    all_companies = db_session.query(Company).all()

    return render_template(
        'delete-company.html',
        all_companies=all_companies,
        company=company,
        error=error,
    )


@app.route('/companies/<int:company_id>/')
@app.route('/companies/<int:company_id>/cards/')
def showCards(company_id):
    all_companies = db_session.query(Company).all()

    company = utils.get_company_by_id(company_id, db_session)

    cards = db_session.query(Card).filter(Card.company_id==company_id).all()

    return render_template(
        'cards.html',
        all_companies=all_companies,
        company=company,
        company_cards=cards,
    )


@app.route('/companies/<int:company_id>/cards/new/', methods=['GET', 'POST'])
def newCard(company_id):
    if 'username' not in session:
        return redirect(
            url_for('login', error='You need to login to add card')
        )

    user = utils.get_user_by_email(session['email'], db_session)
    company = utils.get_company_by_id(company_id, db_session)

    error = request.args.get('error', '')

    if company is None:
        return redirect(url_for('showCompanies'))

    elif request.method == 'POST':
        new_card_name = request.form.get("newCardName")
        new_card_content = request.form.get("newCardContent")

        if new_card_name is None or new_card_name == "" \
           or new_card_content is None or new_card_content == "":
            error = "Please enter valid card name and content"

        else:
            card = Card(
                name=new_card_name,
                content=new_card_content,
                company_id=company.id,
                user_id=user.id,
            )
            db_session.add(card)
            db_session.commit()

            return redirect(url_for('showCards', company_id=company.id))

    all_companies = db_session.query(Company).all()

    return render_template(
        'new-card.html',
        all_companies=all_companies,
        company=company,
        error=error,
    )


@app.route('/companies/<int:company_id>/cards/<int:card_id>/edit/',
           methods=['GET', 'POST'])
def editCard(company_id, card_id):
    if 'username' not in session:
        return redirect(
            url_for('login', error='You need to login to edit card')
        )

    error = request.args.get('error', '')

    user = utils.get_user_by_email(session['email'], db_session)
    company = utils.get_company_by_id(company_id, db_session)
    card = utils.get_card_by_id(card_id, db_session)

    if company is None:
        return redirect(url_for('showCompanies'))

    elif card is None:
        return redirect(url_for('showCards', company_id=company.id))

    elif card.user_id != user.id:
        error = "You can only edit the cards you created"

    elif request.method == 'POST':
        new_card_name = request.form.get("newCardName")
        new_card_content = request.form.get("newCardContent")
        new_card_company_id = request.form.get("newCompanyId")

        if new_card_name is None or new_card_name == "" \
           or new_card_content is None or new_card_content == "":
            error = "Please enter valid card name and content"

        else:
            card.name = new_card_name
            card.content = new_card_content
            card.company_id = new_card_company_id

            db_session.add(card)
            db_session.commit()

            company = utils.get_company_by_id(new_card_company_id, db_session)

            return redirect(url_for('showCards', company_id=card.company_id))

    all_companies = db_session.query(Company).all()

    return render_template(
        'edit-card.html',
        all_companies=all_companies,
        company=company,
        card=card,
        error=error,
    )


@app.route('/companies/<int:company_id>/cards/<int:card_id>/delete/',
           methods=['GET', 'POST'])
def deleteCard(company_id, card_id):
    if 'username' not in session:
        return redirect(
            url_for('login', error='You need to login to delete card')
        )

    error = request.args.get('error', '')

    user = utils.get_user_by_email(session['email'], db_session)
    company = utils.get_company_by_id(company_id, db_session)
    card = utils.get_card_by_id(card_id, db_session)

    if company is None:
        return redirect(url_for('showCompanies'))

    elif card is None:
        return redirect(url_for('showCards', company_id=company.id))

    elif card.user_id != user.id:
        error = "You can only delete the cards you created"

    elif request.method == 'POST' \
         and request.form.get('deleteCard') is not None:
        db_session.delete(card)
        db_session.commit()

        return redirect(url_for('showCards', company_id=company.id))

    all_companies = db_session.query(Company).all()

    return render_template(
        'delete-card.html',
        all_companies=all_companies,
        company=company,
        card=card,
        error=error,
    )


if __name__ == "__main__":
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
