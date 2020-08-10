from flask import Flask, render_template
from flask import request, redirect
from logging.handlers import RotatingFileHandler
from gevent.pywsgi import WSGIServer
from pathlib import Path
from src.salt import hash_password, verify_password
from src.config import config, keys
from src.parser import namnyamParser, foodItem, shortFoodItem
import threading
import json
import time
import logging
import sys
import traceback
import datetime
import requests
import src.database



logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
Path("log/").mkdir(exist_ok=True)

fileHandler = RotatingFileHandler('log/latest.log', mode='a', maxBytes=5242880, backupCount=2)
fileHandler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s:%(name)s:%(message)s'))
logger.addHandler(fileHandler)

def uncaughtExceptionHandler(etype, value, tb):
    formatted_exception = ' '.join(traceback.format_exception(etype, value, tb))
    print(formatted_exception)
    logger.error(f"Uncaught exception: {formatted_exception}")

sys.excepthook = uncaughtExceptionHandler


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
            cart['complex'][title] = {'foods': [shortFoodItem(x[0], x[1], x[2], ID=x[3]) 
                                                for x in db.getComplexItems(' '.join((title, f'{price} руб.')), 'complexItem')],
                                      'price': price, 'ID': itemID, 'amount': amount}
        elif Type == 'menu':
            cart['menu'].append(shortFoodItem(title, price, link, amount=amount, ID=itemID))

    return cart


def updateUserSession(SID: str):
    newdate = datetime.date.today()
    db.updateSessionDate(SID, f'{newdate.year}-{newdate.month}-{newdate.day}')
    sessions[SID]['date'] = newdate


def monthlyClearSessions():
    """
    Clear old sessions monthly.
    Do database vacuum.
    """
    global sessions
    while True:
        sessions = getStoredSessions()
        db.vacuum()
        for _ in range(200):
            time.sleep(1315)


def getStoredSessions() -> dict:
    """
    Pull stored sessions from database, delete sessions older than a month.
    return: sessions dictionary
    """
    sessions = {}
    sessionsToDelete = []
    for s in db.getSessions():
        if s[3] + datetime.timedelta(days=30) < datetime.date.today():
            sessionsToDelete.append((s[0], ))
            continue
        sessions[s[0]] = {'username': s[1], 'usertype': s[2], 'date': s[3]}
    if sessionsToDelete:
        db.deleteSessions(sessionsToDelete)
    return sessions


def dailyMenuUpdate():
    """
    Check nam-nyam menu every hour,
    update if changes.
    """

    # DEBUG
    if keys['DEBUG']:
        return
    keys['DEBUG'] = True
    with open('keys.json', 'w') as o:
        json.dump(keys, o, indent=4)

    global dailycomplex, dailymenu

    while True:

        # DEBUG
        time.sleep(3)
        keys['DEBUG'] = False
        with open('keys.json', 'w') as o:
            json.dump(keys, o, indent=4)

        logger.info('check catering')
        boolDailyMenu = db.checkDailyMenu()

        if not boolDailyMenu:

            logger.info('update menu')
            dailycomplex, dailymenu = namnyamParser().getDailyMenu(requests.get("https://www.nam-nyam.ru/catering/").text)

            complexProducts = []
            for section in dailycomplex.keys():
                section = section.split(' ')
                title = ' '.join(section[:-2])
                price = int(section[-2:-1][0])
                complexProducts.append(shortFoodItem(title, price, 'None'))

            db.clearDailyMenu()

            date = datetime.date.today()
            date = f'{date.year}-{date.month}-{date.day}'

            db.addDailyMenu([(v.title, v.weight, v.calories, v.price, v.link, v.image_link, k, 'complexItem', date) \
                                for k, foods in dailycomplex.items() for v in foods] + \
                                    [(v.title, v.weight, v.calories, v.price, v.link, v.image_link, k, 'menu', date) \
                                        for k, foods in dailymenu.items() for v in foods] + \
                                            [(p.title, 'None', 'None', p.price, 'None', 'None', 'None', 'complex', date) \
                                                for p in complexProducts])

        time.sleep(config['dailyMenuUpdateInterval'])


db = src.database.Database()
sessionSecret = keys['sessionSecret']
sessions = {}

# DEBUG
if keys['DEBUG']:

    dailycomplex = {}
    dailymenu = {}
    old_section = None

    for k, v in {'complexItem': dailycomplex, 'menu': dailymenu}.items():
        for i in db.getDailyMenuByType(k):
            section = i[6]
            food_item = foodItem(i[0], i[1], i[2], i[3], i[4], i[5], ID=i[7])
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

    monthlyClearSessionsThread = threading.Thread(target=monthlyClearSessions)
    monthlyClearSessionsThread.start()

dailyMenuUpdateThread = threading.Thread(target=dailyMenuUpdate)
dailyMenuUpdateThread.start()


app = Flask(__name__)


@app.route('/')
def index():
    """
    Redirect to menu page.
    """
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
        displayname = message.get('displayname')
        password = message.get('password')

        if not (isinstance(displayname, str) and isinstance(password, str)):
            return {'success': False, 'message': 'enter username and password'}

        if not all(0 < len(x) <= 25 for x in [displayname, password]):
            return {'success': False, 'message': 'username/password length = 1-25 chars!'}

        for i in displayname, password:
            for letter in i:
                code = ord(letter)
                if(code == 32):
                    return {'success': False, 'message': 'no spaces please'}
                if (48 <= code <= 57) or (65 <= code <= 90) or (97 <= code <= 122):
                    continue
                return {'success': False, 'message': 'only english characters and numbers'}

        username = displayname.lower()
        userinfo = db.getUser(username)
        if userinfo:
            hashed_pwd = userinfo[1]
            usertype = userinfo[2]
            if verify_password(hashed_pwd, password):
                SID = hash_password(sessionSecret)
                date = datetime.date.today()
                sessions[SID] = {'username': username, 'usertype': usertype, 'date': date}
                db.addSession(SID, username, usertype, f'{date.year}-{date.month}-{date.day}')
                logger.info(f'login user {username}')
                return {'success': True, 'SID': SID}
            else:
                logger.info(f'failed login user {username}')
                return {'success': False, 'message': 'password did not match'}
        else:
            hashed_pwd = hash_password(password)
            SID = hash_password(sessionSecret)
            date = datetime.date.today()
            sessions[SID] = {'username': username, 'usertype': 'user', 'date': date}
            date = f'{date.year}-{date.month}-{date.day}'
            db.addUser(username, displayname, hashed_pwd, 'user', date)
            db.addSession(SID, username, 'user', date)
            logger.info(f'register user {username}')
            return {'success': True, 'SID': SID}


@app.route('/u/<username>')
def linkprofile(username):
    """
    User page checks if user exists,
    updates session and loads profile if session is valid.
    """
    username = username.lower()

    userinfo = db.getUser(username)
    if not userinfo:
        return redirect('/menu', code=302)

    SID = request.cookies.get("SID")
    session = sessions.get(SID)
    if session and session['username'] == username:

        userinfo = {'username': username, 'displayname': userinfo[0]}

        updateUserSession(SID)
        logger.info(f'update session {username}')

        cart = getUserCart(username)
        
        if cart:
            cartSum = db.getUserCartSum(username)
            cart['_SUM'] = cartSum[0]

        return render_template('userprofile.html', auth=True, userinfo=userinfo, cart=cart)
    return redirect('/menu', code=302)


@app.route('/logout', methods=['POST'])
def logout():
    """
    Delete old session cookie or
    delete session from memory and database,
    delete cookie, redirect to index page,
    reload page if session not found.
    """
    try:
        message = request.get_json()
        SID = message.get('SID')
        if not isinstance(SID, str):
            return {'success': False}
        del sessions[SID]
        db.deleteSession(SID)
        return {'success': True}
    except KeyError:
        return {'success': False}


@app.route('/buy', methods=['POST'])
def buy():
    """
    Add items to cart.
    """
    message = request.get_json()
    SID = request.cookies.get("SID")
    session = sessions.get(SID)
    if session:

        if session['usertype'] == 'admin':
            username = message.get('username')
            if not isinstance(username, str):
                return {'success': False, 'message': 'Error: no username'}
        else:
            username = session['username']

        cart_id = db.getUserCartID(username)
        if not cart_id:
            return {'success': False, 'message': 'Error: cart not found'}

        product_id = message.get('productID')
        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            logger.info(f'invalid productID {product_id}')
            return {'success': False, 'message': 'Error: invalid product id.'}

        product_id = db.getProductByID(product_id)
        if not product_id:
            logger.info(f'invalid productID not found {product_id}')
            return {'success': False, 'message': 'Error: product not found'}

        db.addCartProduct(cart_id[0], product_id[0], 1, time.time())

        return {'success': True}

    return {'success': False, 'message': 'Unauthorized'}


@app.route('/menu')
def menu():
    SID = request.cookies.get("SID")
    session = sessions.get(SID)

    if session:
        username = session['username']

        displayname = db.getUserDisplayName(username)
        if not displayname:
            return render_template('menu.html', auth=False, userinfo={}, dailymenu=dailymenu, dailycomplex=dailycomplex)

        updateUserSession(SID)

        cart = getUserCart(username)

        return render_template('menu.html', auth=True, userinfo={'username': username, 'displayname': displayname[0]},
                                            dailymenu=dailymenu, dailycomplex=dailycomplex, cart=cart)
    return render_template('menu.html', auth=False, userinfo={},
                                        dailymenu=dailymenu, dailycomplex=dailycomplex)


# Production

# wsgi = WSGIServer(('0.0.0.0', keys['flaskPort']), app, log=requestLogs, error_log=logger)
# wsgi.serve_forever()

# Debug.
app.run(debug=True, host='127.0.0.1', port=keys['flaskPort'])
