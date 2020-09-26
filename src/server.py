import json
import time
import datetime
from threading import Thread
from typing import Optional

from flask import Flask, render_template, request, redirect, make_response
from gevent.pywsgi import WSGIServer
import requests

import src.database as db
from .salt import hash_password, verify_password
from .config import config, keys
from .log import logger
from .structure import ShortFoodItem, FormResponseHandler, Cookie
from .utils import (seconds_convert, get_catering, clearDB, dailyMenuUpdate, 
    getSession, getSessionAccountShare, getUserCart, getFormData)


catering = get_catering()

monthlyClearDBThread = Thread(target=clearDB)
monthlyClearDBThread.start()

dailyMenuUpdateThread = Thread(target=dailyMenuUpdate)
dailyMenuUpdateThread.start()

app = Flask(__name__)
app.secret_key = keys['sessionSecret']


@app.route('/')
def index():
    return redirect('/menu')


@app.route('/login', methods=['POST'])
def login():
    """
    Login page does signup and login (username+password),
    check if credentials are valid.
    If user exists: verify password, create new session,
    send error message if wrong password.
    Or register user: hash password, create new session,
    add user to database.
    Create cookie and redirect to menu.
    """
    message = getFormData(request)
    redirect_url = request.referrer or '/'
    response = FormResponseHandler(redirect_url, flash_type='login')

    target_user_id = message.get('target')
    if isinstance(target_user_id, int):
        SID = request.cookies.get("SID")
        session = getSession(SID)
        if session:
            target_userinfo = db.getUserByID(target_user_id)
            if not target_userinfo:
                response.message = 'Error: target user not found'
                return response.make_response()
            shareinfo = db.verifyAccountShare(target_user_id, session.user_id)
            if not shareinfo:
                response.message = 'Error: account share not found'
                return response.make_response()
            now = datetime.datetime.now()
            share_interval = shareinfo[0]
            if share_interval is not None:
                share_date = shareinfo[1]
                if share_date + share_interval < now:
                    db.deleteAccountShare(target_user_id, session.user_id)
                    response.message = 'Error: account share is outdated'
                    return response.make_response()
            asID = shareinfo[2]
            SID = hash_password(keys['sessionSecret'])
            db.addSession(SID, now, target_user_id, asID)
            logger.info(f'shared login user {target_userinfo[0]}')
            response.cookie = Cookie('SID', SID)
            return response.make_response()
        response.message = 'Error: Unauthorized'
        return response.make_response()

    displayname = message.get('displayname')
    password = message.get('password')

    if not (isinstance(displayname, str) and isinstance(password, str)):
        response.message = 'Error: enter username and password'
        return response.make_response()

    if not all(0 < len(x) <= 25 for x in [displayname, password]):
        response.message = 'Error: username/password length 1-25 chars'
        return response.make_response()

    for i in displayname, password:
        for letter in i:
            code = ord(letter)
            if code == 32:
                response.message = 'Error: no spaces please'
                return response.make_response()
            if (48 <= code <= 57) or (65 <= code <= 90) or (97 <= code <= 122):
                continue
            response.message = 'Error: only english characters and numbers'
            return response.make_response()

    username = displayname.lower()
    userinfo = db.getUser(username)
    if userinfo:
        hashed_pwd = userinfo[1]
        user_id = userinfo[3]
        if verify_password(hashed_pwd, password):
            SID = hash_password(keys['sessionSecret'])
            db.addSession(SID, datetime.datetime.now(), user_id)
            old_cookie = request.cookies.get('SID')
            if old_cookie:
                db.deleteSession(old_cookie)
            logger.info(f'login user {username}')
            response.cookie = Cookie('SID', SID)
            return response.make_response()
        else:
            logger.info(f'failed login user {username}')
            response.message = 'Error: password did not match'
            return response.make_response()
    else:
        hashed_pwd = hash_password(password)
        SID = hash_password(keys['sessionSecret'])
        date = datetime.datetime.now()
        user_id = db.addUser(username, displayname, hashed_pwd, 'user', date)
        db.addSession(SID, date, user_id[0])
        logger.info(f'register user {username}')
        response.cookie = Cookie('SID', SID)
        return response.make_response()


@app.route('/logout', methods=['POST'])
def logout():
    response = make_response(redirect('/'))
    SID = request.cookies.get('SID')
    session = getSession(SID)
    if session and isinstance(SID, str):
        db.deleteSession(SID)
        response.set_cookie('SID', '', expires=0)
        logger.info(f'logout user {session.username}')
    return response


@app.route('/u/<username>')
def userprofile(username):
    SID = request.cookies.get("SID")
    session = getSession(SID)
    if session and session.username == username.lower():

        userinfo = {
            'auth': True, 
            'username': session.username, 
            'displayname': session.displayname
        }
        userinfo = getSessionAccountShare(session, userinfo)

        return render_template('userprofile.html', userinfo=userinfo)
    return redirect('/menu')


@app.route('/cart', methods=['GET', 'POST'])
def buy():
    SID = request.cookies.get("SID")
    session = getSession(SID)
    if session:
        message = request.get_json()
        username = session.username

        if request.method == 'POST':
            act = message.get('act')
            if all(act != x for x in ['add', 'update', 'clear', 'submit']):
                return {'success': False, 'message': 'Error: invalid cart item action'}

            cart_id = db.getUserCartID(username)
            if not cart_id:
                return {'success': False, 'message': 'Error: cart not found'}

            if act == 'submit':
                user_cart_items = db.getUserCartItems(username)
                if not user_cart_items:
                    return {'success': False, 'message': 'Error: empty cart'}
                order_id = db.addOrder(session.user_id, datetime.datetime.now())
                order_products = [(order_id, x[0], x[1], x[2], x[4]) for x in user_cart_items]
                db.addOrderProducts(order_products)
                db.clearUserCart(cart_id[0])
                return {'success': True}

            if act == 'clear':
                db.clearUserCart(cart_id[0])
                return {'success': True}

            product_id = message.get('productID')
            if not isinstance(product_id, int):
                return {'success': False, 'message': 'Error: invalid product id'}
            product_id = db.getProductByID(product_id)
            if not product_id:
                return {'success': False, 'message': 'Error: product not found'}

            if act == 'add':
                db.addCartProduct(cart_id[0], product_id[0], 1, datetime.datetime.now())
                return {'success': True}

            if act == 'update':
                amount = message.get('amount')
                if not isinstance(amount, int) or not 100 > amount >= 0:
                    return {'success': False, 'message': 'Error: invalid cart item amount'}
                db.updateCartProduct(cart_id[0], product_id[0], amount)
                return {'success': True}
        else:
            userinfo = db.getUser(username)
            cart = getUserCart(username)
            if cart:
                cartSum = db.getUserCartSum(username)
                cart['sum'] = cartSum[0]

            userinfo = {
                'auth': True, 
                'username': username, 
                'displayname': userinfo[0], 
                'cart': cart
            }

            return render_template('cart.html', userinfo=userinfo)
    elif request.method == 'POST':
        return {'success': False, 'message': 'Error: Unauthorized'}
    else:
        return redirect('/menu')


@app.route('/menu')
def menu():
    SID = request.cookies.get("SID")
    session = getSession(SID)
    if session:

        userinfo = {
            'auth': True, 
            'username': session.username, 
            'displayname': session.displayname
        }

        return render_template('menu.html', userinfo=userinfo, catering=catering)
    return render_template('menu.html', userinfo={}, catering=catering)

@app.route('/orders')
def orders_():
    SID = request.cookies.get('SID')
    session = getSession(SID)
    if session:
        orderProducts = db.getOrderProducts(session.user_id)
        orders = {}
        for op in orderProducts:
            title, price, link, amount, order_id, order_date = \
                op[0], op[1], op[2], op[3], op[4], op[5]
            if not orders.get(order_id):
                orders[order_id] = {'products': [], 'order_date': order_date}
            orders[order_id]['products'].append(ShortFoodItem(title, price, link, amount))
        userinfo = {
            'auth': True,
            'orders': orders,
            'username': session.username,
            'displayname': session.displayname
        }
        return render_template('orders.html', userinfo=userinfo)
    return redirect('/menu')

@app.route('/shared', methods=['POST'])
def shared():
    SID = request.cookies.get('SID')
    session = getSession(SID)
    if session:

        message = getFormData(request)
        redirect_url = request.referrer or '/'
        response = FormResponseHandler(redirect_url, flash_type='accountShare')

        act = message.get('act')
        if all(act != x for x in ['add', 'del']):
            response.message = 'Error: invalid account share action'
            return response.make_response()

        if act == 'add':
            username = message.get('username')
            if not username or not isinstance(username, str):
                response.message = 'Error: invalid username'
                return response.make_response()

            target_user_id = db.getUserID(username)
            if not target_user_id or target_user_id[0] == session.user_id:
                response.message = 'Error: invalid target user'
                return response.make_response()

            duration = {'days': message.get('days'), 
                        'hours': message.get('hours'), 
                        'minutes': message.get('minutes'), 
                        'seconds': message.get('seconds')}

            if all(x == "" for x in duration.values()):
                db.addAccountShare(session.user_id, target_user_id[0], None, datetime.datetime.now())
                return response.make_response()

            try:
                for k, v in duration.items():
                    if v == "":
                        v = 0
                    elif not isinstance(v, int):
                        v = int(v)
                    assert 9999 >= v >= 0
                    duration[k] = v
                duration = datetime.timedelta(**duration)
                assert duration.total_seconds() <= 864276039
            except Exception:
                response.message = 'Error: invalid account share duration'
                return response.make_response()

            db.addAccountShare(session.user_id, target_user_id[0], duration, datetime.datetime.now())
            return response.make_response()
        if act == 'del':
            target_user_id = message.get('target')
            if not isinstance(target_user_id, int):
                response.message = 'Error: target user id must be int'
                return response.make_response()

            shareinfo = db.verifyAccountShare(session.user_id, target_user_id)
            if not shareinfo:
                response.message = 'Error: account share not found'
                return response.make_response()

            db.deleteAccountShare(session.user_id, target_user_id)
            return response.make_response()
    response.message = 'Error: Unauthorized'
    return response.make_response()

# Production

# requestLogs = 'default' if config['flaskLogging'] else None

# wsgi = WSGIServer((keys['flaskHost'], keys['flaskPort']), app, log=requestLogs, error_log=logger)
# wsgi.serve_forever()

# Debug.
app.run(debug=True, host=keys['flaskHost'], port=keys['flaskPort'])
