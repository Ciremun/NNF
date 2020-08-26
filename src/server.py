from flask import Flask, render_template, request, redirect
from gevent.pywsgi import WSGIServer
from .salt import hash_password, verify_password
from .config import config, keys
from .log import logger
from .structure import Session, FoodItem, ShortFoodItem
from threading import Thread
import src.parser as parser
import src.database as db
import json
import time
import datetime
import requests


def getUserCart(username) -> dict:
    cartItems = db.getUserCartItems(username)
    if not cartItems:
        return None

    cart = {'complex': {}, 'menu': []}
    for item in cartItems:
        title = item[0]
        price = item[1]
        link = item[2]
        Type = item[3]
        amount = item[4]
        itemID = item[5]

        if Type == 'complex':
            cart['complex'][title] = {'foods': [ShortFoodItem(x[0], x[1], x[2], ID=x[3]) 
                                                for x in db.getComplexItems(' '.join((title, f'{price} руб.')), 'complexItem')],
                                      'price': price, 'ID': itemID, 'amount': amount}
        elif Type == 'menu':
            cart['menu'].append(ShortFoodItem(title, price, link, amount=amount, ID=itemID))

    return cart

def updateUserSession(session: Session):
    now = datetime.datetime.now()
    if session.date < now:
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
    if not SID:
        return
    s = db.getSession(SID)
    if s:
        return Session(SID, s[0], s[1], s[2], s[3])

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
                    return {'success': False, 'message': 'target user not found'}
                shareinfo = db.getAccountShare(target_user_id, session.user_id)
                if not shareinfo:
                    return {'success': False, 'message': 'account share not found'}
                share_interval = shareinfo[0]
                share_date = shareinfo[1]
                now = datetime.datetime.now()
                if share_date + share_interval < now:
                    db.deleteAccountShare(target_user_id, session.user_id)
                    return {'success': False, 'message': 'account share is outdated'}
                username = target_userinfo[0]
                usertype = target_userinfo[2]
                SID = hash_password(sessionSecret)
                db.addSession(SID, username, usertype, now, target_user_id)
                logger.info(f'login user {username}')
                return {'success': True, 'SID': SID}
            return {'success': False, 'message': 'Unauthorized'}

        displayname = message.get('displayname')
        password = message.get('password')

        if not (isinstance(displayname, str) and isinstance(password, str)):
            return {'success': False, 'message': 'enter username and password'}

        if not all(0 < len(x) <= 25 for x in [displayname, password]):
            return {'success': False, 'message': 'username/password length = 1-25 chars!'}

        for i in displayname, password:
            for letter in i:
                code = ord(letter)
                if code == 32:
                    return {'success': False, 'message': 'no spaces please'}
                if (48 <= code <= 57) or (65 <= code <= 90) or (97 <= code <= 122):
                    continue
                return {'success': False, 'message': 'only english characters and numbers'}

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
                return {'success': False, 'message': 'password did not match'}
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

        updateUserSession(session)

        cart = getUserCart(username)
        if cart:
            cartSum = db.getUserCartSum(username)
            cart['_SUM'] = cartSum[0]

        userinfo = {'auth': True, 'username': username, 
                    'displayname': userinfo[0], 'cart': cart}
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

        if session.usertype == 'admin':
            username = message.get('username')
            if not isinstance(username, str):
                return {'success': False, 'message': 'Error: no username'}
        else:
            username = session.username

        act = message.get('act')
        if all(act != x for x in ['add', 'update', 'clear']):
            return {'success': False, 'message': 'Error: invalid cart item action.'}

        cart_id = db.getUserCartID(username)
        if not cart_id:
            return {'success': False, 'message': 'Error: cart not found'}

        if act == 'clear':
            db.clearUserCart(cart_id[0])
            return {'success': True}

        product_id = message.get('productID')
        if not isinstance(product_id, int):
            return {'success': False, 'message': 'Error: invalid product id.'}

        product_id = db.getProductByID(product_id)
        if not product_id:
            return {'success': False, 'message': 'Error: product not found'}

        if act == 'add':
            db.addCartProduct(cart_id[0], product_id[0], 1, datetime.datetime.now())
            return {'success': True}

        if act == 'update':
            amount = message.get('amount')
            if not isinstance(amount, int) or amount < 0:
                return {'success': False, 'message': 'Error: invalid cart item amount.'}
            db.updateCartProduct(cart_id[0], product_id[0], amount)
            return {'success': True}

    return {'success': False, 'message': 'Unauthorized'}


@app.route('/menu')
def menu():
    SID = request.cookies.get("SID")
    session = getSession(SID)
    if session:
        username = session.username

        displayname = db.getUserDisplayName(username)
        if not displayname:
            return render_template('menu.html', userinfo={'auth': False}, catering=catering)

        updateUserSession(session)
        userinfo = {'auth': True, 'username': username, 'displayname': displayname[0]}
        return render_template('menu.html', userinfo=userinfo, catering=catering)

    return render_template('menu.html', userinfo={'auth': False}, catering=catering)


# Production

# requestLogs = 'default' if config['flaskLogging'] else None

# wsgi = WSGIServer((keys['flaskHost'], keys['flaskPort']), app, log=requestLogs, error_log=logger)
# wsgi.serve_forever()

# Debug.
app.run(debug=True, host=keys['flaskHost'], port=keys['flaskPort'])
