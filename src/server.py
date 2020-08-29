import json
import time
import datetime
from threading import Thread

from flask import Flask, render_template, request, redirect
from gevent.pywsgi import WSGIServer
import requests

import src.parser as parser
import src.database as db
from .salt import hash_password, verify_password
from .config import config, keys
from .log import logger
from .structure import Session, FoodItem, ShortFoodItem


def getUserCart(username) -> dict:
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

def monthlyClearSessions():
    while True:
        sessionsToDelete = []
        for s in db.getSessions():
            if s[1] + datetime.timedelta(days=30) < datetime.datetime.now():
                sessionsToDelete.append((s[0], ))
                continue
        if sessionsToDelete:
            db.deleteSessions(sessionsToDelete)
            sessionsToDelete.clear()
        for _ in range(200):
            time.sleep(1315)

def databaseVacuum():
    while True:
        db.vacuum()
        logger.info('vacuum')
        time.sleep(600)

def getSession(SID: str):
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

def getSessionAccountShare(session: Session, userinfo: dict):
    account_share = db.getAccountShare(session.user_id)
    if account_share:
        available, shared_to = {}, {}
        for i in account_share:
            user_id, user, target_user_id, target_user = i[0], i[1], i[2], i[3]
            if user_id == session.user_id:
                shared_to[target_user] = target_user_id
            else:
                available[user] = user_id
        userinfo['account_share'] = {
            'available': available,
            'shared_to': shared_to
        }
    return userinfo

sessionSecret = keys['sessionSecret']
catering = {'complex': {}, 'items': {}}

monthlyClearSessionsThread = Thread(target=monthlyClearSessions)
monthlyClearSessionsThread.start()

dbVacuumThread = Thread(target=databaseVacuum)
dbVacuumThread.start()

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
    if request.method == 'POST':
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
                username = target_userinfo[0]
                usertype = target_userinfo[2]
                SID = hash_password(sessionSecret)
                db.addSession(SID, username, usertype, now, target_user_id, shared=True)
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
def linkprofile(username):
    username = username.lower()

    userinfo = db.getUser(username)
    if not userinfo:
        return redirect('/menu', code=302)

    SID = request.cookies.get("SID")
    session = getSession(SID)
    if session and session.username == username:
        cart = getUserCart(username)
        if cart:
            cartSum = db.getUserCartSum(username)
            cart['sum'] = cartSum[0]

        userinfo = {
            'auth': True, 
            'username': username, 
            'displayname': userinfo[0], 
            'cart': cart,
            'server-date': f'{datetime.datetime.now()}'
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


@app.route('/cart', methods=['POST'])
def buy():
    message = request.get_json()
    SID = request.cookies.get("SID")
    session = getSession(SID)
    if session:
        username = session.username

        act = message.get('act')
        if all(act != x for x in ['add', 'update', 'clear']):
            return {'success': False, 'message': 'Error: invalid cart item action'}

        cart_id = db.getUserCartID(username)
        if not cart_id:
            return {'success': False, 'message': 'Error: cart not found'}

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
            if not isinstance(amount, int) or amount < 0:
                return {'success': False, 'message': 'Error: invalid cart item amount'}
            db.updateCartProduct(cart_id[0], product_id[0], amount)
            return {'success': True}

    return {'success': False, 'message': 'Error: Unauthorized'}


@app.route('/menu')
def menu():
    SID = request.cookies.get("SID")
    session = getSession(SID)
    if session:
        username = session.username

        displayname = db.getUserDisplayName(username)
        if not displayname:
            return render_template('menu.html', userinfo={}, catering=catering)

        userinfo = {
            'auth': True, 
            'username': username, 
            'displayname': displayname[0]
        }
        userinfo = getSessionAccountShare(session, userinfo)

        return render_template('menu.html', userinfo=userinfo, catering=catering)
    return render_template('menu.html', userinfo={}, catering=catering)


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

            d = message.get('duration')
            if not isinstance(d, dict):
                return {'success': False, 'message': 'Error: invalid account share duration'}

            try:
                until_datetime = datetime.datetime(d['year'], d['month'], d['day'], d['hour'], d['minute'], d['second'])
            except KeyError as e:
                return {'success': False, 'message': f'KeyError: account share {e} key not found'}
            except ValueError as e:
                return {'success': False, 'message': f'ValueError: {e}'}

            now = datetime.datetime.now()
            if until_datetime <= now:
                return {'success': False, 'message': 'Error: given date expired'}
            duration = until_datetime - now

            db.addAccountShare(session.user_id, target_user_id[0], duration, now)
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
