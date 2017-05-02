# -*- coding: utf-8 -*-

def create_user(login_session=login_session, session=sesson):
    new_user = User(
        name=login_session['username'],
        email=login_session['email'],
        picture=login_session['picture'],
        provider=login_session['provider'],
    )
    session.add(new_user)
    session.commit()
    # user = session.query(User).filter_by(email=login_session['email']).one()
    # return user.id


def get_user_by_id(user_id):
    try:
        user = session.query(User).filter_by(id=user_id).one()
        return user
    except:
        return None


def get_user_id_by_email(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


def get_company_by_id(company_id):
    try:
        company = session.query(Company).filter_by(id=company_id).one()
        return company
    except:
        return None
