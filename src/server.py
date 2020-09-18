import json
import time
import datetime
from threading import Thread
from typing import Optional

from flask import Flask, render_template, request, redirect
from gevent.pywsgi import WSGIServer
import requests

import src.parser as parser
import src.database as db
from .salt import hash_password, verify_password
from .config import config, keys
from .log import logger
from .structure import Session, FoodItem, ShortFoodItem
from .utils import seconds_convert


def getUserCart(username: str) -> dict:
    cartItems = db.getUserCartItems(username)
    if not cartItems:
        return

    cart = {'complex': {}, 'menu': []}
    for i in cartItems:
        title, price, link, Type, amount, itemID = i[0], i[1], i[2], i[3], i[4], i[5]
        if Type == 'complex':
            cart['complex'][title] = {'foods': [ShortFoodItem(x[0], x[1], x[2], ID=x[3]) 
                                                for x in db.getComplexItems(' '.join((title, f'{price} руб.')), 'complexItem')],
                                      'price': price, 'ID': itemID, 'amount': amount}
        elif Type == 'menu':
            cart['menu'].append(ShortFoodItem(title, price, link, amount=amount, ID=itemID))

    return cart

def updateUserSession(session: Session):
    now = datetime.datetime.now()
    if session.date.day < now.day:
        db.updateSessionDate(session.SID, now)
        logger.info(f'update session {session.username}')

def clearDB():
    """
    Delete old sessions, account share, do vacuum.
    """
    while True:
        sessionsToDelete = []
        accountShareToDelete = []
        now = datetime.datetime.now()
        for s in db.getSessions():
            sessionID = s[0]
            sessionDate = s[1]
            if sessionDate + datetime.timedelta(days=30) <= now:
                sessionsToDelete.append((sessionID, ))
        for a in db.getAccountShares():
            asID = a[0]
            asDuration = a[1]
            asDate = a[2]
            if asDuration is not None and asDate + asDuration <= now:
                accountShareToDelete.append((asID,))
        if sessionsToDelete:
            db.deleteSessions(sessionsToDelete)
            sessionsToDelete.clear()
        if accountShareToDelete:
            db.deleteAccountShares(accountShareToDelete)
            accountShareToDelete.clear()
        db.vacuum()
        logger.debug('clearDB')
        time.sleep(60)

def getSession(SID: str) -> Optional[Session]:
    if not isinstance(SID, str):
        return
    s = db.getSession(SID)
    if s:
        session = Session(SID, s[0], s[1], s[2], s[3])
        updateUserSession(session)
        return session

def dailyMenuUpdate():
    global catering
    init_catering()

    while True:

        boolDailyMenu = db.checkDailyMenu()

        if not boolDailyMenu:

            logger.info('update menu')
            catering = parser.getDailyMenu(requests.get("https://www.nam-nyam.ru/catering/").text)

            complexProducts = []
            for section in catering['complex'].keys():
                section = section.split(' ')
                title = ' '.join(section[:-2])
                price = int(section[-2:-1][0])
                complexProducts.append(ShortFoodItem(title, price, 'None'))

            db.clearDailyMenu()

            date = datetime.datetime.now()

            db.addDailyMenu([(v.title, v.weight, v.calories, v.price, v.link, v.image_link, k, 'complexItem', date) \
                                for k, foods in catering['complex'].items() for v in foods] + \
                                    [(v.title, v.weight, v.calories, v.price, v.link, v.image_link, k, 'menu', date) \
                                        for k, foods in catering['items'].items() for v in foods] + \
                                            [(p.title, 'None', 'None', p.price, 'None', 'None', 'None', 'complex', date) \
                                                for p in complexProducts])

        time.sleep(config['dailyMenuUpdateInterval'])

def init_catering():
    global catering
    old_section = None

    for k, v in {'complexItem': catering['complex'], 'menu': catering['items']}.items():
        for i in db.getDailyMenuByType(k):
            section = i[6]
            food_item = FoodItem(i[0], i[1], i[2], i[3], i[4], i[5], ID=i[7])
            if section != old_section:
                if k == 'complexItem':
                    v[section] = {}
                    v[section]['foods'] = []
                    v[section]['foods'].append(food_item)
                    split_ = section.split(' ')
                    product_id = db.getProductID(' '.join(split_[:-2]), int(split_[-2:-1][0]), 'complex')
                    v[section]['ID'] = product_id[0]
                else:
                    v[section] = []
                    v[section].append(food_item)
                old_section = section
                continue
            if k == 'complexItem':
                v[section]['foods'].append(food_item)
            else:
                v[section].append(food_item)

def getSessionAccountShare(session: Session, userinfo: dict) -> dict:
    account_share = db.getAccountShareByID(session.user_id)
    if account_share:
        available, shared_to = {}, {}
        for i in account_share:
            user_id, user, target_user_id, target_user, \
                s_Duration, s_Date = i[0], i[1], i[2], i[3], i[4], i[5]
            if user_id == session.user_id:
                if s_Duration is None:
                    duration = 'Бессрочно'
                else:
                    now = datetime.datetime.now()
                    expiration_date = s_Date + s_Duration
                    if expiration_date <= now:
                        duration = 'Истек'
                    else:
                        seconds_left = (expiration_date - now).total_seconds()
                        duration = seconds_convert(seconds_left)
                shared_to[target_user] = {'id': target_user_id, 
                                          'duration': duration}
            else:
                available[user] = user_id
        userinfo['account_share'] = {
            'available': available,
            'shared_to': shared_to
        }
    return userinfo

sessionSecret = keys['sessionSecret']
catering = {'complex': {}, 'items': {}}

monthlyClearDBThread = Thread(target=clearDB)
monthlyClearDBThread.start()

dailyMenuUpdateThread = Thread(target=dailyMenuUpdate)
dailyMenuUpdateThread.start()

app = Flask(__name__)

@app.route('/')
def index():
    return redirect('/menu', code=302)


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
    message = request.get_json()

    target_user_id = message.get('target')
    if isinstance(target_user_id, int):
        SID = request.cookies.get("SID")
        session = getSession(SID)
        if session:
            target_userinfo = db.getUserByID(target_user_id)
            if not target_userinfo:
                return {'success': False, 'message': 'Error: target user not found'}
            shareinfo = db.verifyAccountShare(target_user_id, session.user_id)
            if not shareinfo:
                return {'success': False, 'message': 'Error: account share not found'}
            now = datetime.datetime.now()
            share_interval = shareinfo[0]
            if share_interval is not None:
                share_date = shareinfo[1]
                if share_date + share_interval < now:
                    db.deleteAccountShare(target_user_id, session.user_id)
                    return {'success': False, 'message': 'Error: account share is outdated'}
            asID = shareinfo[2]
            username = target_userinfo[0]
            usertype = target_userinfo[2]
            SID = hash_password(sessionSecret)
            db.addSession(SID, username, usertype, now, target_user_id, asID)
            logger.info(f'shared login user {username}')
            return {'success': True, 'SID': SID}
        return {'success': False, 'message': 'Error: Unauthorized'}

    displayname = message.get('displayname')
    password = message.get('password')

    if not (isinstance(displayname, str) and isinstance(password, str)):
        return {'success': False, 'message': 'Error: enter username and password'}

    if not all(0 < len(x) <= 25 for x in [displayname, password]):
        return {'success': False, 'message': 'Error: username/password length 1-25 chars'}

    for i in displayname, password:
        for letter in i:
            code = ord(letter)
            if code == 32:
                return {'success': False, 'message': 'Error: no spaces please'}
            if (48 <= code <= 57) or (65 <= code <= 90) or (97 <= code <= 122):
                continue
            return {'success': False, 'message': 'Error: only english characters and numbers'}

    username = displayname.lower()
    userinfo = db.getUser(username)
    if userinfo:
        hashed_pwd = userinfo[1]
        usertype = userinfo[2]
        user_id = userinfo[3]
        if verify_password(hashed_pwd, password):
            SID = hash_password(sessionSecret)
            db.addSession(SID, username, usertype, datetime.datetime.now(), user_id)
            logger.info(f'login user {username}')
            return {'success': True, 'SID': SID}
        else:
            logger.info(f'failed login user {username}')
            return {'success': False, 'message': 'Error: password did not match'}
    else:
        hashed_pwd = hash_password(password)
        SID = hash_password(sessionSecret)
        date = datetime.datetime.now()
        user_id = db.addUser(username, displayname, hashed_pwd, 'user', date)
        db.addSession(SID, username, 'user', date, user_id[0])
        logger.info(f'register user {username}')
        return {'success': True, 'SID': SID}


@app.route('/u/<username>')
def userprofile(username):
    username = username.lower()
    userinfo = db.getUser(username)

    SID = request.cookies.get("SID")
    session = getSession(SID)
    if session and session.username == username:

        userinfo = {
            'auth': True, 
            'username': username, 
            'displayname': userinfo[0]
        }
        userinfo = getSessionAccountShare(session, userinfo)

        return render_template('userprofile.html', userinfo=userinfo)
    return redirect('/menu', code=302)


@app.route('/logout', methods=['POST'])
def logout():
    message = request.get_json()
    SID = message.get('SID')
    if not isinstance(SID, str):
        return {'success': False}
    db.deleteSession(SID)
    return {'success': True}


@app.route('/cart', methods=['GET', 'POST'])
def buy():
    message = request.get_json()
    SID = request.cookies.get("SID")
    session = getSession(SID)
    if session:
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
        return redirect('/menu', code=302)


@app.route('/menu')
def menu():
    SID = request.cookies.get("SID")
    session = getSession(SID)
    if session:

        userinfo = {
            'auth': True, 
            'username': session.username, 
            'displayname': session.username # @@@ refactor sessions table
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
            'displayname': session.username # @@@ refactor sessions table
        }
        return render_template('orders.html', userinfo=userinfo)
    return redirect('/menu')

@app.route('/shared', methods=['POST'])
def shared():
    message = request.get_json()
    SID = request.cookies.get('SID')
    session = getSession(SID)
    if session:
        act = message.get('act')
        if all(act != x for x in ['add', 'del']):
            return {'success': False, 'message': 'Error: invalid account share action'}

        if act == 'add':
            username = message.get('username')
            if not username or not isinstance(username, str):
                return {'success': False, 'message': 'Error: invalid username'}

            target_user_id = db.getUserID(username)
            if not target_user_id or target_user_id[0] == session.user_id:
                return {'success': False, 'message': 'Error: invalid target user'}

            if message.get('forever') == True:
                db.addAccountShare(session.user_id, target_user_id[0], None, datetime.datetime.now())
                return {'success': True}

            d = message.get('duration')
            try:
                assert isinstance(d, dict)
                assert len(d) == 4
                assert all(isinstance(v, int) and v >= 0 for v in [d.get('days'), d.get('hours'), d.get('minutes'), d.get('seconds')])
                duration = datetime.timedelta(**d)
                assert duration.total_seconds() <= 864276039
            except AssertionError:
                return {'success': False, 'message': 'Error: invalid account share duration'}

            db.addAccountShare(session.user_id, target_user_id[0], duration, datetime.datetime.now())
            return {'success': True}
        if act == 'del':
            target_user_id = message.get('target')
            if not isinstance(target_user_id, int):
                return {'success': False, 'message': 'Error: target user id must be int'}

            shareinfo = db.verifyAccountShare(session.user_id, target_user_id)
            if not shareinfo:
                return {'success': False, 'message': 'Error: account share not found'}

            db.deleteAccountShare(session.user_id, target_user_id)
            return {'success': True}
    return {'success': False, 'message': 'Error: Unauthorized'}

# Production

# requestLogs = 'default' if config['flaskLogging'] else None

# wsgi = WSGIServer((keys['flaskHost'], keys['flaskPort']), app, log=requestLogs, error_log=logger)
# wsgi.serve_forever()

# Debug.
app.run(debug=True, host=keys['flaskHost'], port=keys['flaskPort'])
