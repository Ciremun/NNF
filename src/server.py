from flask import Flask, render_template
from flask import request, redirect
from logging.handlers import RotatingFileHandler
from gevent.pywsgi import WSGIServer
from pathlib import Path
from src.salt import hash_password, verify_password
from src.config import config, keys
from src.parser import namnyamParser, foodItem
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


def getStoredSessions():
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


def dailyUpdateMenu():
    """
    Update nam-nyam menu daily.
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

        dailyMenuDate = db.getDailyMenuDate()

        if not dailyMenuDate or dailyMenuDate[0] < datetime.date.today():

            dailycomplex, dailymenu = namnyamParser().getDailyMenu(requests.get("https://www.nam-nyam.ru/catering/").text)

            complexProducts = []
            for section in dailycomplex.keys():
                section = section.split(' ')
                title = ' '.join(section[:-2])
                price = int(section[-2:-1][0])
                complexProducts.append(foodItem(title, 'None', 'None', price, 'None', 'None'))

            db.clearDailyMenu()

            date = datetime.date.today()
            date = f'{date.year}-{date.month}-{date.day}'

            db.addDailyMenu([(v.title, v.weight, v.calories, v.price, v.link, v.image_link, k, 'complexItem', date) \
                                for k, foods in dailycomplex.items() for v in foods] + \
                                    [(v.title, v.weight, v.calories, v.price, v.link, v.image_link, k, 'menu', date) \
                                        for k, foods in dailymenu.items() for v in foods] + \
                                            [(p.title, p.weight, p.calories, p.price, p.link, p.image_link, 'None', 'complex', date) \
                                                for p in complexProducts])

        now = datetime.datetime.today()
        end = datetime.datetime(now.year, now.month, now.day, 23, 59, 59, 0)
        sleep_for = (end - now).total_seconds()
        time.sleep(sleep_for)


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

dailyUpdateMenuThread = threading.Thread(target=dailyUpdateMenu)
dailyUpdateMenuThread.start()


app = Flask(__name__)


@app.route('/')
def index():
    """
    Index page checks for a session cookie,
    redirect to userprofile (if cookie found) or login page.
    """
    SID = request.cookies.get("SID")
    session = sessions.get(SID)
    if session:
        return redirect(f'/u/{session["username"]}', code=302)
    return redirect('/login', code=302)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page does signup and login (username+password),
    check if credentials are valid.
    If user exists: verify password, create new session,
    send error message if wrong password.
    Or register user: hash password, create new session,
    add user to database.
    Create cookie and redirect to profile.
    """
    if request.method == 'POST':
        message = request.get_json()
        username = message['username']
        password = message['password']

        if not (username and password):
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
                return {'success': True, 'username': username, 'SID': SID}
            else:
                logger.info(f'failed login user {username}')
                return {'success': False, 'message': 'password did not match'}
        else:
            hashed_pwd = hash_password(password)
            SID = hash_password(sessionSecret)
            date = datetime.date.today()
            sessions[SID] = {'username': username, 'usertype': 'user', 'date': date}
            db.addUser(username, message["displayname"], hashed_pwd, 'user')
            db.addSession(SID, username, 'user', f'{date.year}-{date.month}-{date.day}')
            logger.info(f'register user {username}')
            return {'success': True, 'username': username, 'SID': SID}
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
        newdate = datetime.date.today()
        db.updateSessionDate(SID, f'{newdate.year}-{newdate.month}-{newdate.day}')
        sessions[SID]['date'] = newdate
        return render_template('userprofile.html', username=username, displayname=userinfo[0],
                                dailymenu=dailymenu, dailycomplex=dailycomplex)
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
        del sessions[message['SID']]
        db.deleteSession(message['SID'])
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
        if not Type:
            return {'success': False, 'message': 'Error: no item type'}

        if session['usertype'] == 'admin':
            username = message.get('username')
            if not username:
                return {'success': False, 'message': 'Error: no username'}
        else:
            username = session['username']

        item = message.get("item")
        price = message.get("price")

        if not (item and price):
            return {'success': False, 'message': 'Error: product not found'}

        try:
            price = int(price)
        except ValueError:
            return {'success': False, 'message': 'Error: price is not a number'}

        if Type == 'complex':

            item = db.getDailyMenuByTitlePriceType(item, price, 'complex')
            if not item:
                return {'success': False, 'message': 'Error: product not found'}

            # title, price = item
            # complexItems = db.getDailyMenuBySectionAndType(' '.join((title, price)), 'complexItem')
            # add complex item to cart
            return {'success': True}
        elif Type == 'menu':
            # add menu item to cart
            pass

    return {'success': False, 'message': 'Unauthorized'}


# Production
# requestLogs = 'default' if config['flaskLogging'] else None

# wsgi = WSGIServer(('0.0.0.0', keys['flaskPort']), app, log=requestLogs, error_log=logger)
# wsgi.serve_forever()

# Debug
app.run(debug=True, host='0.0.0.0', port=keys['flaskPort'])
