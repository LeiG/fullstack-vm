# -*- coding: utf-8 -*-

from database_setup import User, Company


def create_user(session, db_session):
    new_user = User(
        name=session['username'],
        email=session['email'],
        picture=session['picture'],
        provider=session['provider'],
    )
    db_session.add(new_user)
    db_session.commit()
    # user = session.query(User).filter_by(email=login_session['email']).one()
    # return user.id


def get_user_by_id(user_id, db_session):
    try:
        user = db_session.query(User).filter_by(id=user_id).one()
        return user
    except:
        return None


def get_user_id_by_email(email, db_session):
    try:
        user = db_session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


def get_company_by_id(company_id, db_session):
    try:
        company = db_session.query(Company).filter_by(id=company_id).one()
        return company
    except:
        return None
