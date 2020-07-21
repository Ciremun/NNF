from flask import Flask, render_template
from flask import request, redirect
from logging.handlers import RotatingFileHandler
from gevent.pywsgi import WSGIServer
from src.salt import hash_password, verify_password
from src.config import config
from pathlib import Path
import threading
import json
import time
import logging
import sys
import traceback
import datetime
import requests
import src.database
import src.parser


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


dailymenu = src.parser.namnyamParser().getDailyMenu(requests.get("https://www.nam-nyam.ru/catering/").text)

def monthlyClearSessions():
    """
    Clear old sessions monthly.
    """
    global sessions
    while True:
        sessions = getStoredSessions()
        for _ in range(200):
            time.sleep(1315)

def getDatetimeDateObject(dbDate: str):
    year, month, day = [int(x) for x in dbDate.split('-')]
    return datetime.date(year, month, day)

def getStoredSessions():
    """
    Pull stored sessions from database, delete sessions older than a month.
    return: sessions dictionary
    """
    sessions = {}
    sessionsToDelete = []
    for s in db.getSessions():
        s_date = getDatetimeDateObject(s[3])
        if s_date + datetime.timedelta(days=30) < datetime.date.today():
            sessionsToDelete.append((s[0], ))
            continue
        sessions[s[0]] = {'username': s[1], 'usertype': s[2], 'date': s_date}
    if sessionsToDelete:
        db.deleteSessions(sessionsToDelete)
    return sessions

db = src.database.Database()
sessionSecret = json.load(open('keys.json'))['sessionSecret']
sessions = {}

monthlyClearSessionsThread = threading.Thread(target=monthlyClearSessions)
monthlyClearSessionsThread.start()

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
    Login page does signup and login (username+password)
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
                return {'status': 200, 'username': username, 'SID': SID}
            else:
                logger.info(f'failed login user {username}')
                return {'status': 401}
        else:
            hashed_pwd = hash_password(password)
            SID = hash_password(sessionSecret)
            date = datetime.date.today()
            sessions[SID] = {'username': username, 'usertype': 'user', 'date': date}
            db.addUser(username, message["displayname"], hashed_pwd, 'user')
            db.addSession(SID, username, 'user', f'{date.year}-{date.month}-{date.day}')
            logger.info(f'register user {username}')
            return {'status': 200, 'username': username, 'SID': SID}
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
        session['date'] = newdate
        db.updateSessionDate(SID, f'{newdate.year}-{newdate.month}-{newdate.day}')
        return render_template('userprofile.html', username=username, displayname=userinfo[0], dailymenu=dailymenu)
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
        return {'status': 200}
    except KeyError:
        return {'status': 404}

# Production
# requestLogs = 'default' if config['flaskLogging'] else None

# wsgi = WSGIServer(('0.0.0.0', config['flaskPort']), app, log=requestLogs, error_log=logger)
# wsgi.serve_forever()

# Debug
app.run(debug=True, host='0.0.0.0', port=config['flaskPort'])
