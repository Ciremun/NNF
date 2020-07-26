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
        return False

    cartSum = db.getUserCartSum(username)

    cart = {'complex': {}, 'menu': []}
    for item in cartItems:
        title = item[0]
        price = item[1]
        link = item[2]
        Type = item[3]

        if Type == 'complex':
            cart['complex'][title] = {'foods': [shortFoodItem(x[0], x[1], x[2]) 
                                                for x in db.getComplexItems(' '.join((title, f'{price} руб.')), 'complexItem')],
                                      'price': price}
        elif Type == 'menu':
            cart['menu'].append(shortFoodItem(title, price, link))

        cart['_SUM'] = cartSum[0]

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
    it = None

    for k, v in {'complexItem': dailycomplex, 'menu': dailymenu}.items():
        for i in db.getDailyMenuByType(k):
            if i[6] != it:
                v[i[6]] = []
                v[i[6]].append(foodItem(i[0], i[1], i[2], i[3], i[4], i[5]))
                it = i[6]
                continue
            v[i[6]].append(foodItem(i[0], i[1], i[2], i[3], i[4], i[5]))

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


@app.route('/login', methods=['GET', 'POST'])
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
        username = message.get('username')
        password = message.get('password')

        if not (isinstance(username, str) and isinstance(password, str)):
            return {'success': False, 'message': 'enter username and password'}

        if any(len(x) > 25 for x in [username, password]):
            return {'success': False, 'message': 'max username/password length = 25!'}

        for i in username, password:
            for letter in i:
                code = ord(letter)
                if(code == 32):
                    return {'success': False, 'message': 'no spaces please'}
                if (48 <= code <= 57) or (65 <= code <= 90) or (97 <= code <= 122):
                    continue
                return {'success': False, 'message': 'only english characters and numbers'}

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
            displayname = message.get('displayname')
            if not isinstance(displayname, str):
                return {'success': False, 'message': 'invalid displayname'}
            hashed_pwd = hash_password(password)
            SID = hash_password(sessionSecret)
            date = datetime.date.today()
            sessions[SID] = {'username': username, 'usertype': 'user', 'date': date}
            date = f'{date.year}-{date.month}-{date.day}'
            db.addUser(username, displayname, hashed_pwd, 'user', date)
            db.addSession(SID, username, 'user', date)
            logger.info(f'register user {username}')
            return {'success': True, 'SID': SID}
    return render_template('login.html')


@app.route('/u/<username>')
def linkprofile(username):
    """
    User page checks if user exists,
    updates session and loads profile if session is valid.
    """
    username = username.lower()

    userinfo = db.getUser(username)
    if not userinfo:
        return "User not found"

    SID = request.cookies.get("SID")
    session = sessions.get(SID)
    if session and (session['username'] == username or session['usertype'] == 'admin'):

        userinfo = {'username': username, 'displayname': userinfo[0]}

        updateUserSession(SID)
        logger.info(f'update session {username}')

        cart = getUserCart(username)
        if not cart:
            return render_template('userprofile.html', auth=True, userinfo=userinfo, cart=None)

        return render_template('userprofile.html', auth=True, userinfo=userinfo, cart=cart)
    return "401 Unauthorized"


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

        Type = message.get('type')
        if not isinstance(Type, str):
            return {'success': False, 'message': 'Error: no item type'}

        if session['usertype'] == 'admin':
            username = message.get('username')
            if not isinstance(username, str):
                return {'success': False, 'message': 'Error: no username'}
        else:
            username = session['username']

        item = message.get("item")
        price = message.get("price")

        if not (isinstance(item, str) and isinstance(price, str)):
            return {'success': False, 'message': 'Error: product not found'}

        try:
            price = int(price)
        except ValueError:
            return {'success': False, 'message': 'Error: price is not a number'}

        if any(x == Type for x in ['menu', 'complex']):

            cart_id = db.getUserCartID(username)
            if not cart_id:
                return {'success': False, 'message': 'Error: cart not found'}

            product_id = db.getProductID(item, price, Type)
            if not product_id:
                return {'success': False, 'message': 'Error: product not found'}

            db.addCartProduct(cart_id[0], product_id[0])

            return {'success': True}
        else:
            return {'success': False, 'message': 'Error: unknown item type'}

    return {'success': False, 'message': 'Unauthorized'}


@app.route('/menu')
def menu():
    SID = request.cookies.get("SID")
    session = sessions.get(SID)
    auth = False
    userinfo = {}

    if session:
        username = session['username']

        displayname = db.getUserDisplayName(username)
        if not displayname:
            return render_template('menu.html', auth=auth, userinfo=userinfo, dailymenu=dailymenu, dailycomplex=dailycomplex)

        auth = True
        userinfo = {'username': username, 'displayname': displayname[0]}
        updateUserSession(SID)

    return render_template('menu.html', auth=auth, userinfo=userinfo, dailymenu=dailymenu, dailycomplex=dailycomplex)


@app.route('/cart')
def cart():
    """
    Currently mimics userprofile.
    """
    SID = request.cookies.get("SID")
    session = sessions.get(SID)
    if session:

        username = session['username']

        displayname = db.getUserDisplayName(username)
        if not displayname:
            return render_template('menu.html', auth=False, userinfo={}, dailymenu=dailymenu, dailycomplex=dailycomplex)

        userinfo = {'username': username, 'displayname': displayname[0]}

        updateUserSession(SID)
        logger.info(f'update session {username}')

        cart = getUserCart(username)
        if not cart:
            return render_template('userprofile.html', auth=True, userinfo=userinfo, cart=None)

        return render_template('userprofile.html', auth=True, userinfo=userinfo, cart=cart)
    return "401 Unauthorized"

# Production
# requestLogs = 'default' if config['flaskLogging'] else None

# wsgi = WSGIServer(('0.0.0.0', keys['flaskPort']), app, log=requestLogs, error_log=logger)
# wsgi.serve_forever()

# Debug
app.run(debug=True, host='0.0.0.0', port=keys['flaskPort'])
