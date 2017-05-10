# -*- coding: utf-8 -*-

from database_setup import User, Company


def create_user(session, db_session):
    new_user = User(
        username=session['username'],
        email=session['email'],
        picture=session['picture'],
        provider=session['provider'],
    )
    db_session.add(new_user)
    db_session.commit()


def get_user_by_id(user_id, db_session):
    try:
        user = db_session.query(User).filter_by(id=user_id).one()
        return user
    except:
        return None


def get_user_by_email(email, db_session):
    try:
        user = db_session.query(User).filter_by(email=email).one()
        return user
    except:
        return None


def get_company_by_id(company_id, db_session):
    try:
        company = db_session.query(Company).filter_by(id=company_id).one()
        return company
    except:
        return None
